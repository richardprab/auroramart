from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class ChatSession(models.Model):
    """A chat session between a user and admin"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chat_sessions')
    title = models.CharField(max_length=200, default="New Chat")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['-updated_at']
    
    def __str__(self):
        return f"Chat #{self.id} - {self.user.username}"
    
    @property
    def unread_count(self):
        """Count unread messages for the user"""
        return self.messages.filter(is_read=False, is_from_admin=True).count()
    
    @property
    def last_message(self):
        """Get the last message in this session"""
        return self.messages.order_by('-created_at').first()


class ChatMessage(models.Model):
    """Individual chat messages"""
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='messages')
    message = models.TextField()
    is_from_admin = models.BooleanField(default=False)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['created_at']
    
    def __str__(self):
        sender = "Admin" if self.is_from_admin else self.session.user.username
        return f"{sender}: {self.message[:50]}"
