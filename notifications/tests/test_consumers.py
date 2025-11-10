import json
from channels.testing import WebsocketCommunicator
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from django.test import TransactionTestCase
from notifications.consumers import NotificationConsumer
from notifications.models import Notification

User = get_user_model()


class NotificationConsumerTest(TransactionTestCase):
    """Test WebSocket consumer for notifications."""

    def setUp(self):
        """Set up test user."""
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123"
        )

    async def test_websocket_connection_authenticated(self):
        """Test WebSocket connection with authenticated user."""
        communicator = WebsocketCommunicator(
            NotificationConsumer.as_asgi(),
            "/ws/notifications/"
        )
        communicator.scope["user"] = self.user
        
        connected, subprotocol = await communicator.connect()
        self.assertTrue(connected)
        
        # Should receive initial unread count
        response = await communicator.receive_json_from()
        self.assertEqual(response["type"], "unread_count")
        self.assertIn("count", response)
        
        await communicator.disconnect()

    async def test_websocket_connection_unauthenticated(self):
        """Test WebSocket connection with unauthenticated user."""
        communicator = WebsocketCommunicator(
            NotificationConsumer.as_asgi(),
            "/ws/notifications/"
        )
        communicator.scope["user"] = None
        
        connected, subprotocol = await communicator.connect()
        # Connection should be rejected
        self.assertFalse(connected)
        
        await communicator.disconnect()

    async def test_receive_notification_message(self):
        """Test receiving notification message via WebSocket."""
        communicator = WebsocketCommunicator(
            NotificationConsumer.as_asgi(),
            "/ws/notifications/"
        )
        communicator.scope["user"] = self.user
        
        connected, subprotocol = await communicator.connect()
        self.assertTrue(connected)
        
        # Receive initial unread count
        await communicator.receive_json_from()
        
        # Create a notification
        notification = await database_sync_to_async(Notification.objects.create)(
            user=self.user,
            message="Test notification",
            notification_type="platform"
        )
        
        # Send notification message to group
        from channels.layers import get_channel_layer
        channel_layer = get_channel_layer()
        
        group_name = f"notifications_{self.user.id}"
        await channel_layer.group_send(
            group_name,
            {
                "type": "notification_message",
                "notification": {
                    "id": notification.id,
                    "message": notification.message,
                    "link": notification.link or "",
                    "notification_type": notification.notification_type,
                    "is_read": notification.is_read,
                    "created_at": notification.created_at.isoformat(),
                }
            }
        )
        
        # Receive notification message
        response = await communicator.receive_json_from()
        self.assertEqual(response["type"], "notification")
        self.assertIn("notification", response)
        self.assertEqual(response["notification"]["message"], "Test notification")
        
        await communicator.disconnect()

    async def test_receive_unread_count_update(self):
        """Test receiving unread count update via WebSocket."""
        communicator = WebsocketCommunicator(
            NotificationConsumer.as_asgi(),
            "/ws/notifications/"
        )
        communicator.scope["user"] = self.user
        
        connected, subprotocol = await communicator.connect()
        self.assertTrue(connected)
        
        # Receive initial unread count
        initial_response = await communicator.receive_json_from()
        self.assertEqual(initial_response["type"], "unread_count")
        initial_count = initial_response["count"]
        
        # Create a notification
        await database_sync_to_async(Notification.objects.create)(
            user=self.user,
            message="Test notification",
            notification_type="platform"
        )
        
        # Send unread count update to group
        from channels.layers import get_channel_layer
        channel_layer = get_channel_layer()
        
        group_name = f"notifications_{self.user.id}"
        unread_count = await database_sync_to_async(
            Notification.objects.filter(user=self.user, is_read=False).count
        )()
        
        await channel_layer.group_send(
            group_name,
            {
                "type": "unread_count_update",
                "count": unread_count,
            }
        )
        
        # Receive unread count update
        response = await communicator.receive_json_from()
        self.assertEqual(response["type"], "unread_count")
        self.assertEqual(response["count"], initial_count + 1)
        
        await communicator.disconnect()

    async def test_ping_pong(self):
        """Test ping/pong message handling."""
        communicator = WebsocketCommunicator(
            NotificationConsumer.as_asgi(),
            "/ws/notifications/"
        )
        communicator.scope["user"] = self.user
        
        connected, subprotocol = await communicator.connect()
        self.assertTrue(connected)
        
        # Receive initial unread count
        await communicator.receive_json_from()
        
        # Send ping
        await communicator.send_json_to({"type": "ping"})
        
        # Receive pong
        response = await communicator.receive_json_from()
        self.assertEqual(response["type"], "pong")
        
        await communicator.disconnect()

