from rest_framework import serializers
from .models import ChatSession, ChatMessage


class ChatMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatMessage
        fields = ['id', 'message', 'is_from_admin', 'is_read', 'created_at']
        read_only_fields = ['id', 'created_at', 'is_from_admin']


class ChatSessionSerializer(serializers.ModelSerializer):
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()
    
    class Meta:
        model = ChatSession
        fields = ['id', 'title', 'created_at', 'updated_at', 'is_active', 'last_message', 'unread_count']
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_last_message(self, obj):
        last_msg = obj.last_message
        if last_msg:
            return {
                'message': last_msg.message,
                'is_from_admin': last_msg.is_from_admin,
                'created_at': last_msg.created_at
            }
        return None
    
    def get_unread_count(self, obj):
        # Check if it's from annotated queryset first
        if hasattr(obj, 'unread_messages_count'):
            return obj.unread_messages_count
        # Fallback to property
        return obj.unread_count


class ChatSessionDetailSerializer(serializers.ModelSerializer):
    messages = ChatMessageSerializer(many=True, read_only=True)
    unread_count = serializers.SerializerMethodField()
    
    class Meta:
        model = ChatSession
        fields = ['id', 'title', 'created_at', 'updated_at', 'is_active', 'messages', 'unread_count']
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_unread_count(self, obj):
        # Check if it's from annotated queryset first
        if hasattr(obj, 'unread_messages_count'):
            return obj.unread_messages_count
        # Fallback to property
        return obj.unread_count
