from django.urls import path
from . import views

app_name = "notifications"

urlpatterns = [
    path("", views.notification_list, name="notification_list"),
    path("<int:pk>/read/", views.mark_notification_read, name="mark_read"),
    path("mark-all-read/", views.mark_all_read, name="mark_all_read"),
    path("api/unread-count/", views.get_unread_count, name="unread_count"),
]
