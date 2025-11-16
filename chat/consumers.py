import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model

User = get_user_model()


class ChatConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for real-time chat messages."""

    async def connect(self):
        self.user = self.scope.get("user")
        
        if not self.user or not self.user.is_authenticated:
            await self.close()
            return
        
        self.group_name = f"chat_{self.user.id}"
        
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        
        await self.accept()
        
        unread_count = await self.get_unread_count()
        await self.send(text_data=json.dumps({
            "type": "unread_count",
            "count": unread_count
        }))

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name
            )

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            if data.get("type") == "ping":
                await self.send(text_data=json.dumps({"type": "pong"}))
        except json.JSONDecodeError:
            pass

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            "type": "chat_message",
            "message": event["message"],
            "conversation_id": event["conversation_id"]
        }))

    async def unread_count_update(self, event):
        await self.send(text_data=json.dumps({
            "type": "unread_count",
            "count": event["count"]
        }))

    @database_sync_to_async
    def get_unread_count(self):
        from .models import ChatConversation
        return ChatConversation.objects.filter(
            user=self.user,
            user_has_unread=True
        ).count()


class AdminChatConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for admin panel real-time chat messages."""

    async def connect(self):
        self.user = self.scope.get("user")
        
        if not self.user or not self.user.is_authenticated:
            await self.close()
            return
        
        if not (self.user.is_staff or self.user.is_superuser):
            await self.close()
            return
        
        url_route = self.scope.get("url_route", {})
        kwargs = url_route.get("kwargs", {})
        self.conversation_id = kwargs.get("conversation_id")
        
        if not self.conversation_id:
            path = self.scope.get("path", "")
            import re
            match = re.search(r'/ws/admin/chat/(\d+)/', path)
            if match:
                self.conversation_id = int(match.group(1))
        
        if not self.conversation_id:
            await self.close()
            return
        
        try:
            self.conversation_id = int(self.conversation_id)
        except (ValueError, TypeError):
            await self.close()
            return
        
        has_access = await self.check_conversation_access()
        if not has_access:
            await self.close()
            return
        
        self.group_name = f"admin_chat_{self.conversation_id}"
        
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name
            )

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            if data.get("type") == "ping":
                await self.send(text_data=json.dumps({"type": "pong"}))
        except json.JSONDecodeError:
            pass

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            "type": "chat_message",
            "message": event["message"],
            "conversation_id": event["conversation_id"]
        }))

    @database_sync_to_async
    def check_conversation_access(self):
        from .models import ChatConversation
        from accounts.models import Staff
        
        try:
            conversation = ChatConversation.objects.get(id=self.conversation_id)
            if self.user.is_superuser:
                return True
            if isinstance(self.user, Staff):
                return conversation.admin == self.user
            return False
        except ChatConversation.DoesNotExist:
            return False

