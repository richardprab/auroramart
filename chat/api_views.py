from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q, Count
from .models import ChatSession, ChatMessage
from .serializers import (
    ChatSessionSerializer, 
    ChatSessionDetailSerializer, 
    ChatMessageSerializer
)


class ChatSessionViewSet(viewsets.ModelViewSet):
    """ViewSet for managing chat sessions"""
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return ChatSessionDetailSerializer
        return ChatSessionSerializer
    
    def get_queryset(self):
        """Only return sessions for the current user"""
        return ChatSession.objects.filter(
            user=self.request.user
        ).annotate(
            unread_count=Count('messages', filter=Q(messages__is_read=False, messages__is_from_admin=True))
        )
    
    def create(self, request, *args, **kwargs):
        """Create a new chat session for the user"""
        # Check if user already has an active session
        active_session = ChatSession.objects.filter(
            user=request.user,
            is_active=True
        ).first()
        
        if active_session:
            serializer = self.get_serializer(active_session)
            return Response(serializer.data)
        
        # Create new session
        session = ChatSession.objects.create(
            user=request.user,
            title=f"Chat with Support"
        )
        serializer = self.get_serializer(session)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'])
    def send_message(self, request, pk=None):
        """Send a message in this chat session"""
        session = self.get_object()
        message_text = request.data.get('message', '').strip()
        
        if not message_text:
            return Response(
                {'error': 'Message cannot be empty'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        message = ChatMessage.objects.create(
            session=session,
            message=message_text,
            is_from_admin=False,
            is_read=False
        )
        
        serializer = ChatMessageSerializer(message)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'])
    def mark_as_read(self, request, pk=None):
        """Mark all admin messages in this session as read"""
        session = self.get_object()
        updated = ChatMessage.objects.filter(
            session=session,
            is_from_admin=True,
            is_read=False
        ).update(is_read=True)
        
        return Response({'marked_read': updated})
    
    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        """Get total unread message count across all sessions"""
        count = ChatMessage.objects.filter(
            session__user=request.user,
            is_from_admin=True,
            is_read=False
        ).count()
        
        return Response({'unread_count': count})
