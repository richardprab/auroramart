from django.contrib import admin
from django.contrib.auth import get_user_model
from django.utils.html import format_html
from .models import Notification

User = get_user_model()


class NotificationAdmin(admin.ModelAdmin):
    list_display = ['user', 'notification_type', 'message_preview', 'is_read', 'created_at']
    list_filter = ['notification_type', 'is_read', 'created_at']
    search_fields = ['user__username', 'user__email', 'message']
    readonly_fields = ['created_at']
    date_hierarchy = 'created_at'
    actions = ['mark_as_read', 'mark_as_unread']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')
    
    def message_preview(self, obj):
        """Display truncated message preview"""
        if len(obj.message) > 50:
            return format_html('<span title="{}">{}</span>', obj.message, obj.message[:50] + '...')
        return obj.message
    message_preview.short_description = 'Message'
    
    def mark_as_read(self, request, queryset):
        """Mark selected notifications as read"""
        count = queryset.update(is_read=True)
        self.message_user(request, f'{count} notification(s) marked as read.')
    mark_as_read.short_description = 'Mark selected notifications as read'
    
    def mark_as_unread(self, request, queryset):
        """Mark selected notifications as unread"""
        count = queryset.update(is_read=False)
        self.message_user(request, f'{count} notification(s) marked as unread.')
    mark_as_unread.short_description = 'Mark selected notifications as unread'


# Only register if not already registered
if not admin.site.is_registered(Notification):
    admin.site.register(Notification, NotificationAdmin)
