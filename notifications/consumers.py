import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model

User = get_user_model()


class NotificationConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for real-time notifications.
    Handles connection, disconnection, and sending notifications to users.
    """

    async def connect(self):
        """
        Handle WebSocket connection.
        Authenticate user and add to their notification group.
        """
        # Get user from scope (set by AuthMiddlewareStack)
        self.user = self.scope.get("user")
        
        # Reject connection if user is not authenticated
        if not self.user or not self.user.is_authenticated:
            await self.close()
            return
        
        # Create group name for this user's notifications
        self.group_name = f"notifications_{self.user.id}"
        
        # Add user to their notification group
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        
        # Accept the WebSocket connection
        await self.accept()
        
        # Send initial unread count
        unread_count = await self.get_unread_count()
        await self.send(text_data=json.dumps({
            "type": "unread_count",
            "count": unread_count
        }))

    async def disconnect(self, close_code):
        """
        Handle WebSocket disconnection.
        Remove user from their notification group.
        """
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name
            )

    async def receive(self, text_data):
        """
        Handle messages received from WebSocket.
        Currently not used, but can be extended for client-to-server messages.
        """
        try:
            data = json.loads(text_data)
            message_type = data.get("type")
            
            if message_type == "ping":
                # Respond to ping with pong
                await self.send(text_data=json.dumps({
                    "type": "pong"
                }))
        except json.JSONDecodeError:
            pass

    async def notification_message(self, event):
        """
        Handle notification message from group.
        Send notification data to WebSocket.
        """
        await self.send(text_data=json.dumps({
            "type": "notification",
            "notification": event["notification"]
        }))

    async def unread_count_update(self, event):
        """
        Handle unread count update from group.
        Send updated count to WebSocket.
        """
        await self.send(text_data=json.dumps({
            "type": "unread_count",
            "count": event["count"]
        }))

    @database_sync_to_async
    def get_unread_count(self):
        """Get unread notification count for the user."""
        from .models import Notification
        return Notification.objects.filter(
            user=self.user,
            is_read=False
        ).count()


