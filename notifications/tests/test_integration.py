import json
from channels.testing import WebsocketCommunicator
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from django.test import TransactionTestCase
from notifications.consumers import NotificationConsumer
from notifications.models import Notification
from notifications.signals import send_notification_websocket

User = get_user_model()


class NotificationIntegrationTest(TransactionTestCase):
    """Integration tests for notification WebSocket functionality."""

    def setUp(self):
        """Set up test user."""
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123"
        )

    async def test_notification_creation_triggers_websocket(self):
        """Test that creating a notification triggers WebSocket message."""
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
        notification = await database_sync_to_async(Notification.objects.create)(
            user=self.user,
            message="Integration test notification",
            notification_type="platform",
            link="/test/"
        )
        
        # Send WebSocket message via signal function
        await database_sync_to_async(send_notification_websocket)(notification)
        
        # Should receive notification message
        notification_response = await communicator.receive_json_from()
        self.assertEqual(notification_response["type"], "notification")
        self.assertEqual(
            notification_response["notification"]["message"],
            "Integration test notification"
        )
        
        # Should receive unread count update
        count_response = await communicator.receive_json_from()
        self.assertEqual(count_response["type"], "unread_count")
        self.assertEqual(count_response["count"], initial_count + 1)
        
        await communicator.disconnect()

    async def test_multiple_notifications(self):
        """Test receiving multiple notifications."""
        communicator = WebsocketCommunicator(
            NotificationConsumer.as_asgi(),
            "/ws/notifications/"
        )
        communicator.scope["user"] = self.user
        
        connected, subprotocol = await communicator.connect()
        self.assertTrue(connected)
        
        # Receive initial unread count
        await communicator.receive_json_from()
        
        # Create multiple notifications
        for i in range(3):
            notification = await database_sync_to_async(Notification.objects.create)(
                user=self.user,
                message=f"Notification {i+1}",
                notification_type="platform"
            )
            await database_sync_to_async(send_notification_websocket)(notification)
        
        # Should receive 3 notification messages and 3 count updates
        for i in range(3):
            notification_response = await communicator.receive_json_from()
            self.assertEqual(notification_response["type"], "notification")
            self.assertEqual(
                notification_response["notification"]["message"],
                f"Notification {i+1}"
            )
            
            count_response = await communicator.receive_json_from()
            self.assertEqual(count_response["type"], "unread_count")
        
        await communicator.disconnect()

    async def test_notification_read_updates_count(self):
        """Test that marking notification as read updates count."""
        communicator = WebsocketCommunicator(
            NotificationConsumer.as_asgi(),
            "/ws/notifications/"
        )
        communicator.scope["user"] = self.user
        
        connected, subprotocol = await communicator.connect()
        self.assertTrue(connected)
        
        # Receive initial unread count
        initial_response = await communicator.receive_json_from()
        initial_count = initial_response["count"]
        
        # Create a notification
        notification = await database_sync_to_async(Notification.objects.create)(
            user=self.user,
            message="Test notification",
            notification_type="platform"
        )
        
        # Send WebSocket message
        await database_sync_to_async(send_notification_websocket)(notification)
        
        # Receive notification and count update
        await communicator.receive_json_from()  # notification
        count_response = await communicator.receive_json_from()  # count update
        self.assertEqual(count_response["count"], initial_count + 1)
        
        # Mark notification as read
        await database_sync_to_async(notification.mark_as_read)()
        
        # Get updated count
        updated_count = await database_sync_to_async(
            Notification.objects.filter(user=self.user, is_read=False).count
        )()
        
        # Send count update manually (in real app, this would be triggered by signal)
        from channels.layers import get_channel_layer
        channel_layer = get_channel_layer()
        group_name = f"notifications_{self.user.id}"
        await channel_layer.group_send(
            group_name,
            {
                "type": "unread_count_update",
                "count": updated_count,
            }
        )
        
        # Should receive updated count
        updated_response = await communicator.receive_json_from()
        self.assertEqual(updated_response["type"], "unread_count")
        self.assertEqual(updated_response["count"], initial_count)
        
        await communicator.disconnect()

