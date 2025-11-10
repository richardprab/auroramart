from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
import json

from .models import ChatConversation, ChatMessage


@require_http_methods(["GET"])
@login_required
def list_conversations(request):
    """List all conversations for the authenticated user"""
    conversations = ChatConversation.objects.filter(
        user=request.user
    ).select_related('admin', 'product').order_by('-updated_at')
    
    data = []
    for conv in conversations:
        messages_data = []
        for msg in conv.messages.all().select_related('sender')[:50]:  # Last 50 messages
            messages_data.append({
                'id': msg.id,
                'content': msg.content,
                'sender': msg.sender.id,
                'created_at': msg.created_at.isoformat(),
            })
        
        data.append({
            'id': conv.id,
            'subject': conv.subject,
            'message_type': conv.message_type,
            'status': conv.status,
            'user_has_unread': conv.user_has_unread,
            'admin_has_unread': conv.admin_has_unread,
            'created_at': conv.created_at.isoformat(),
            'updated_at': conv.updated_at.isoformat(),
            'messages': messages_data,
        })
    
    return JsonResponse({'results': data})


@require_http_methods(["POST"])
@login_required
def create_conversation(request):
    """Create a new conversation"""
    try:
        data = json.loads(request.body)
        subject = data.get('subject', 'New Conversation')
        
        # Auto-assign to staff using round-robin
        from adminpanel.views import get_next_assigned_staff
        next_staff = get_next_assigned_staff()
        
        conversation = ChatConversation.objects.create(
            user=request.user,
            subject=subject,
            admin=next_staff,
        )
        
        return JsonResponse({
            'id': conversation.id,
            'subject': conversation.subject,
            'message_type': conversation.message_type,
            'status': conversation.status,
            'user_has_unread': conversation.user_has_unread,
            'admin_has_unread': conversation.admin_has_unread,
            'created_at': conversation.created_at.isoformat(),
            'updated_at': conversation.updated_at.isoformat(),
            'messages': [],
        }, status=201)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@require_http_methods(["GET"])
@login_required
def get_conversation(request, conversation_id):
    """Get a specific conversation with all messages"""
    conversation = get_object_or_404(
        ChatConversation.objects.select_related('admin', 'product'),
        id=conversation_id,
        user=request.user
    )
    
    messages_data = []
    for msg in conversation.messages.all().select_related('sender'):
        messages_data.append({
            'id': msg.id,
            'content': msg.content,
            'sender': msg.sender.id,
            'created_at': msg.created_at.isoformat(),
        })
    
    return JsonResponse({
        'id': conversation.id,
        'subject': conversation.subject,
        'message_type': conversation.message_type,
        'status': conversation.status,
        'user_has_unread': conversation.user_has_unread,
        'admin_has_unread': conversation.admin_has_unread,
        'created_at': conversation.created_at.isoformat(),
        'updated_at': conversation.updated_at.isoformat(),
        'messages': messages_data,
    })


@require_http_methods(["POST"])
@login_required
def send_message(request, conversation_id):
    """Send a message in a conversation"""
    conversation = get_object_or_404(
        ChatConversation,
        id=conversation_id,
        user=request.user
    )
    
    try:
        data = json.loads(request.body)
        content = data.get('content', '').strip()
        
        if not content:
            return JsonResponse({'error': 'Message content is required'}, status=400)
        
        message = ChatMessage.objects.create(
            conversation=conversation,
            sender=request.user,
            content=content
        )
        
        # Update conversation status
        conversation.status = 'pending'
        conversation.admin_has_unread = True
        conversation.save()
        
        return JsonResponse({
            'id': message.id,
            'content': message.content,
            'sender': message.sender.id,
            'created_at': message.created_at.isoformat(),
        }, status=201)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@require_http_methods(["POST"])
@login_required
def mark_conversation_read(request, conversation_id):
    """Mark conversation as read for the user"""
    conversation = get_object_or_404(
        ChatConversation,
        id=conversation_id,
        user=request.user
    )
    
    conversation.user_has_unread = False
    conversation.save()
    
    return JsonResponse({'success': True})


@require_http_methods(["DELETE"])
@login_required
def delete_conversation(request, conversation_id):
    """Delete a conversation"""
    conversation = get_object_or_404(
        ChatConversation,
        id=conversation_id,
        user=request.user
    )
    
    conversation.delete()
    
    return JsonResponse({'success': True}, status=204)
