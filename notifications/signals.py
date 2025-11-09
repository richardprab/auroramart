from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from datetime import timedelta
from accounts.models import ChatMessage
from products.models import ProductVariant
from .models import Notification


@receiver(post_save, sender=ChatMessage)
def create_chat_notification(sender, instance, created, **kwargs):
    """
    Create notification when admin sends a message to customer
    """
    if not created:
        return
    
    # Only create notification if message is from staff (admin)
    if instance.sender.is_staff:
        # Notify the customer (conversation user)
        customer = instance.conversation.user
        if customer != instance.sender:  # Don't notify if customer sent the message
            Notification.objects.create(
                user=customer,
                message=f"You have a new message from support team",
                link=f"/notifications/",  # Could link to chat or notification page
                notification_type="message"
            )


@receiver(post_save, sender=ProductVariant)
def check_wishlist_sale(sender, instance, created, **kwargs):
    """
    Check if product went on sale and notify users who wishlisted it
    Only trigger if compare_price was set/changed (indicating sale)
    """
    if created:
        return  # Don't check for new variants
    
    # Check if this variant has a compare_price (meaning it's on sale)
    if instance.compare_price and instance.compare_price > instance.price:
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
                Notification.objects.create(
                    user=wishlist_item.user,
                    message=f"🎉 {instance.product.name} is now on sale! Save {discount_percent}%",
                    link=f"/products/{instance.product.slug}/",
                    notification_type="sale"
                )

