from django.db import models
from django.conf import settings
from django.utils import timezone


class ChatConversation(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name="chat_conversations"
    )
    subject = models.CharField(max_length=255, default="General Inquiry")
    is_closed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ["-updated_at"]
        indexes = [
            models.Index(fields=["user", "-updated_at"]),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.subject}"
    
    def get_unread_count(self, user):
        """Get count of unread messages for this conversation"""
        return self.messages.filter(is_read=False).exclude(sender=user).count()


class ChatMessage(models.Model):
    conversation = models.ForeignKey(
        ChatConversation,
        on_delete=models.CASCADE,
        related_name="messages"
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sent_messages"
    )
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["conversation", "created_at"]),
        ]
    
    def __str__(self):
        return f"{self.sender.username}: {self.message[:50]}"


class Notification(models.Model):
    NOTIFICATION_TYPES = [
        ("platform", "Platform Update"),
        ("sale", "Sale Alert"),
        ("stock", "Back in Stock"),
        ("message", "New Message"),
        ("order", "Order Update"),
        ("review", "Review Response"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications"
    )
    message = models.TextField()
    link = models.CharField(max_length=255, blank=True, null=True)
    notification_type = models.CharField(
        max_length=20, choices=NOTIFICATION_TYPES, default="platform"
    )
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "-created_at"]),
            models.Index(fields=["user", "is_read"]),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.notification_type} - {self.created_at}"

    def mark_as_read(self):
        if not self.is_read:
            self.is_read = True
            self.save(update_fields=["is_read"])
