from django.db import models
from django.conf import settings


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

    @classmethod
    def create_notification(cls, user, message, notification_type="platform", link=None):
        """
        Helper method to create a notification and send it via WebSocket.
        
        Args:
            user: User instance to notify
            message: Notification message text
            notification_type: Type of notification (default: "platform")
            link: Optional link URL for the notification
        
        Returns:
            Notification instance
        """
        notification = cls.objects.create(
            user=user,
            message=message,
            notification_type=notification_type,
            link=link or ""
        )
        
        # Send via WebSocket if available
        try:
            from .signals import send_notification_websocket
            send_notification_websocket(notification)
        except Exception:
            # If WebSocket fails, notification is still created
            pass
        
        return notification
