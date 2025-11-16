from django.db.models.signals import post_save
from django.dispatch import receiver
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .models import ChatMessage, ChatConversation

channel_layer = get_channel_layer()


def send_chat_message_websocket(message):
    """
    Send chat message via WebSocket to the user's chat group.
    """
    if channel_layer is None:
        return
    
    conversation = message.conversation
    user = conversation.user
    
    group_name = f"chat_{user.id}"
    
    # Refresh from database to ensure we have the latest data
    message.refresh_from_db()
    
    # Determine if message is from staff
    # Primary check: staff_sender field
    is_staff_message = message.staff_sender is not None
    
    # Fallback: if staff_sender is None but sender exists and has staff permissions
    if not is_staff_message and message.sender:
        is_staff_message = getattr(message.sender, 'is_staff', False) or getattr(message.sender, 'is_superuser', False)
    
    # Additional fallback: if both staff_sender and sender are None, check conversation admin
    # This handles cases where superuser sends message but no Staff instance is available
    if not is_staff_message and message.staff_sender is None and message.sender is None:
        # If conversation has an admin assigned, it's likely a staff message
        # (messages from admin panel typically have admin assigned)
        is_staff_message = conversation.admin is not None
    
    # Prepare message data
    message_data = {
        "id": message.id,
        "content": message.content,
        "sender": message.actual_sender.id if message.actual_sender else None,
        "is_staff": is_staff_message,
        "created_at": message.created_at.isoformat(),
    }
    
    # Send chat message
    async_to_sync(channel_layer.group_send)(
        group_name,
        {
            "type": "chat_message",
            "message": message_data,
            "conversation_id": conversation.id,
        }
    )
    
    # Update unread count
    unread_count = ChatConversation.objects.filter(
        user=user,
        user_has_unread=True
    ).count()
    
    # Send unread count update
    async_to_sync(channel_layer.group_send)(
        group_name,
        {
            "type": "unread_count_update",
            "count": unread_count,
        }
    )


@receiver(post_save, sender=ChatMessage)
def send_chat_message_on_create(sender, instance, created, **kwargs):
    """
    Send chat message via WebSocket when a new message is created.
    """
    if created:
        # Update conversation unread status first
        conversation = instance.conversation
        # If message is from staff, mark as unread for user
        if instance.staff_sender:
            conversation.user_has_unread = True
            conversation.save(update_fields=['user_has_unread'])
        # If message is from user, mark as unread for admin
        elif instance.sender:
            conversation.admin_has_unread = True
            conversation.save(update_fields=['admin_has_unread'])
        
        # Send via WebSocket
        send_chat_message_websocket(instance)

