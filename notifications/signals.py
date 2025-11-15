from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone
from datetime import timedelta
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from chat.models import ChatMessage
from products.models import ProductVariant
from .models import Notification

channel_layer = get_channel_layer()


def send_notification_websocket(notification):
    """
    Send notification via WebSocket to the user's notification group.
    """
    if channel_layer is None:
        return
    
    group_name = f"notifications_{notification.user.id}"
    
    # Prepare notification data
    notification_data = {
        "id": notification.id,
        "message": notification.message,
        "link": notification.link or "",
        "notification_type": notification.notification_type,
        "is_read": notification.is_read,
        "created_at": notification.created_at.isoformat(),
    }
    
    # Get unread count
    unread_count = Notification.objects.filter(
        user=notification.user,
        is_read=False
    ).count()
    
    # Send notification message
    async_to_sync(channel_layer.group_send)(
        group_name,
        {
            "type": "notification_message",
            "notification": notification_data,
        }
    )
    
    # Send unread count update
    async_to_sync(channel_layer.group_send)(
        group_name,
        {
            "type": "unread_count_update",
            "count": unread_count,
        }
    )


@receiver(post_save, sender=ChatMessage)
def create_chat_notification(sender, instance, created, **kwargs):
    """
    Create notification when admin sends a message to customer
    """
    if not created:
        return
    
    # Only create notification if message is from staff (admin)
    actual_sender = instance.actual_sender
    if actual_sender and hasattr(actual_sender, 'is_staff') and actual_sender.is_staff:
        # Notify the customer (conversation user)
        customer = instance.conversation.user
        if customer != actual_sender:  # Don't notify if customer sent the message
            notification = Notification.objects.create(
                user=customer,
                message=f"You have a new message from support team",
                link=f"/notifications/",  # Could link to chat or notification page
                notification_type="message"
            )
            # Send WebSocket message
            send_notification_websocket(notification)


# Store old instance state before save
_old_variant_state = {}


@receiver(pre_save, sender=ProductVariant)
def store_variant_state(sender, instance, **kwargs):
    """Store the old state of the variant before saving"""
    if instance.pk:
        try:
            old_instance = ProductVariant.objects.get(pk=instance.pk)
            _old_variant_state[instance.pk] = {
                'price': old_instance.price,
                'compare_price': old_instance.compare_price,
                'was_on_sale': old_instance.compare_price and old_instance.compare_price > old_instance.price
            }
        except ProductVariant.DoesNotExist:
            pass


@receiver(post_save, sender=ProductVariant)
def check_wishlist_sale(sender, instance, created, **kwargs):
    """
    Check if product went on sale and notify users who wishlisted it
    Only trigger if price or compare_price was actually changed (indicating new sale)
    """
    if created:
        return  # Don't check for new variants
    
    # Only trigger if price or compare_price fields were updated
    # This prevents notifications when only stock or other fields are updated
    update_fields = kwargs.get('update_fields', None)
    if update_fields is not None:
        # If update_fields is specified, only proceed if price or compare_price were updated
        if 'price' not in update_fields and 'compare_price' not in update_fields:
            # Clean up stored state
            _old_variant_state.pop(instance.pk, None)
            return
    
    # Check if the variant is currently on sale
    is_on_sale = instance.compare_price and instance.compare_price > instance.price
    if not is_on_sale:
        # Clean up stored state
        _old_variant_state.pop(instance.pk, None)
        return
    
    # Check if it was already on sale before (using stored state)
    old_state = _old_variant_state.get(instance.pk, {})
    was_on_sale = old_state.get('was_on_sale', False)
    old_price = old_state.get('price')
    old_compare_price = old_state.get('compare_price')
    
    # Only notify if it just went on sale (wasn't on sale before, but is now)
    if was_on_sale:
        # Was already on sale, check if prices changed
        if old_price == instance.price and old_compare_price == instance.compare_price:
            # Prices didn't change, just a stock update or other field
            _old_variant_state.pop(instance.pk, None)
            return
    
    # Clean up stored state
    _old_variant_state.pop(instance.pk, None)
    
    # Get all users who have this product in their wishlist
    from accounts.models import Wishlist
    wishlists = Wishlist.objects.filter(product=instance.product).select_related('user')
    
    # Calculate discount percentage
    discount_percent = int(((instance.compare_price - instance.price) / instance.compare_price) * 100)
    
    for wishlist_item in wishlists:
        # Check if notification already exists for this sale (prevent spam)
        existing = Notification.objects.filter(
            user=wishlist_item.user,
            notification_type='sale',
            link=f'/products/{instance.product.slug}/',
            created_at__gte=timezone.now() - timedelta(hours=24)  # Within last 24 hours
        ).exists()
        
        if not existing:
            notification = Notification.objects.create(
                user=wishlist_item.user,
                message=f"{instance.product.name} is now on sale! Save {discount_percent}%",
                link=f"/products/{instance.product.slug}/",
                notification_type="sale"
            )
            # Send WebSocket message
            send_notification_websocket(notification)

