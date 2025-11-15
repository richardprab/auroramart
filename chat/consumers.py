import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model

User = get_user_model()


class ChatConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for real-time chat messages.
    Handles connection, disconnection, and sending chat messages to users.
    """

    async def connect(self):
        """
        Handle WebSocket connection.
        Authenticate user and add to their chat group.
        """
        # Get user from scope (set by AuthMiddlewareStack)
        self.user = self.scope.get("user")
        
        # Reject connection if user is not authenticated
        if not self.user or not self.user.is_authenticated:
            await self.close()
            return
        
        # Create group name for this user's chat messages
        self.group_name = f"chat_{self.user.id}"
        
        # Add user to their chat group
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
        Remove user from their chat group.
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

    async def chat_message(self, event):
        """
        Handle chat message from group.
        Send message data to WebSocket.
        """
        await self.send(text_data=json.dumps({
            "type": "chat_message",
            "message": event["message"],
            "conversation_id": event["conversation_id"]
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
        """Get unread chat conversation count for the user."""
        from .models import ChatConversation
        return ChatConversation.objects.filter(
            user=self.user,
            user_has_unread=True
        ).count()

