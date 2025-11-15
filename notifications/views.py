from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .models import Notification


@login_required
def mark_notification_read(request, pk):
    """Mark a single notification as read"""
    notification = get_object_or_404(Notification, pk=pk, user=request.user)
    notification.mark_as_read()

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JsonResponse({"status": "success"})

    # Redirect to the notification link if it exists, otherwise home
    if notification.link:
        return redirect(notification.link)
    return redirect("home:index")


@login_required
def mark_all_read(request):
    """Mark all notifications as read"""
    if request.method == "POST":
        request.user.notifications.filter(is_read=False).update(is_read=True)
        
        # Send WebSocket update for unread count
        channel_layer = get_channel_layer()
        if channel_layer:
            group_name = f"notifications_{request.user.id}"
            unread_count = 0  # All are now read
            async_to_sync(channel_layer.group_send)(
                group_name,
                {
                    "type": "unread_count_update",
                    "count": unread_count,
                }
            )

        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({"status": "success"})

        return redirect("home:index")
    return redirect("home:index")


@login_required
def get_unread_count(request):
    """API endpoint for navbar badge count"""
    count = request.user.notifications.filter(is_read=False).count()
    return JsonResponse({"count": count})


@login_required
def get_recent_notifications(request):
    """API endpoint for dropdown - get recent notifications"""
    notifications = request.user.notifications.all()[:10]  # Last 10 notifications
    
    data = []
    for notif in notifications:
        data.append({
            'id': notif.id,
            'message': notif.message,
            'notification_type': notif.notification_type,
            'is_read': notif.is_read,
            'link': notif.link,
            'created_at': notif.created_at.isoformat(),
        })
    
    return JsonResponse({"notifications": data})
