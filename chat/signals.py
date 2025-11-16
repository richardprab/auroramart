from django.db.models.signals import post_save
from django.dispatch import receiver
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .models import ChatMessage, ChatConversation

channel_layer = get_channel_layer()


def send_chat_message_websocket(message):
    """Send chat message via WebSocket to customer and admin groups."""
    if channel_layer is None:
        return
    
    conversation = message.conversation
    user = conversation.user
    
    message.refresh_from_db()
    
    is_staff_message = message.staff_sender is not None
    
    if not is_staff_message and message.sender:
        is_staff_message = getattr(message.sender, 'is_staff', False) or getattr(message.sender, 'is_superuser', False)
    
    if not is_staff_message and message.staff_sender is None and message.sender is None:
        is_staff_message = conversation.admin is not None
    
    sender_name = None
    if message.staff_sender:
        sender_name = message.staff_sender.username.upper()
    elif message.sender:
        sender_name = message.sender.get_full_name() or message.sender.username
    
    message_data = {
        "id": message.id,
        "content": message.content,
        "sender": message.actual_sender.id if message.actual_sender else None,
        "sender_name": sender_name,
        "is_staff": is_staff_message,
        "created_at": message.created_at.isoformat(),
    }
    
    customer_group_name = f"chat_{user.id}"
    async_to_sync(channel_layer.group_send)(
        customer_group_name,
        {
            "type": "chat_message",
            "message": message_data,
            "conversation_id": conversation.id,
        }
    )
    
    admin_group_name = f"admin_chat_{conversation.id}"
    async_to_sync(channel_layer.group_send)(
        admin_group_name,
        {
            "type": "chat_message",
            "message": message_data,
            "conversation_id": conversation.id,
        }
    )
    
    unread_count = ChatConversation.objects.filter(
        user=user,
        user_has_unread=True
    ).count()
    
    async_to_sync(channel_layer.group_send)(
        customer_group_name,
        {
            "type": "unread_count_update",
            "count": unread_count,
        }
    )


@receiver(post_save, sender=ChatMessage)
def send_chat_message_on_create(sender, instance, created, **kwargs):
    """Send chat message via WebSocket when a new message is created."""
    if created:
        conversation = instance.conversation
        if instance.staff_sender:
            conversation.user_has_unread = True
            conversation.save(update_fields=['user_has_unread'])
        elif instance.sender:
            conversation.admin_has_unread = True
            conversation.save(update_fields=['admin_has_unread'])
        
        send_chat_message_websocket(instance)

