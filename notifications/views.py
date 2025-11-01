from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from .models import Notification


@login_required
def notification_list(request):
    """Display all notifications for the user"""
    notifications = request.user.notifications.all()
    unread_count = notifications.filter(is_read=False).count()

    context = {
        "notifications": notifications,
        "unread_count": unread_count,
    }
    return render(request, "notifications/notification_list.html", context)


@login_required
def mark_notification_read(request, pk):
    """Mark a single notification as read"""
    notification = get_object_or_404(Notification, pk=pk, user=request.user)
    notification.mark_as_read()

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JsonResponse({"status": "success"})

    # Redirect to the notification link if it exists
    if notification.link:
        return redirect(notification.link)
    return redirect("notifications:notification_list")


@login_required
def mark_all_read(request):
    """Mark all notifications as read"""
    if request.method == "POST":
        request.user.notifications.filter(is_read=False).update(is_read=True)

        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({"status": "success"})

        return redirect("notifications:notification_list")
    return redirect("notifications:notification_list")


@login_required
def get_unread_count(request):
    """API endpoint for navbar badge count"""
    count = request.user.notifications.filter(is_read=False).count()
    return JsonResponse({"count": count})
