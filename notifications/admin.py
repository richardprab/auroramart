from django.contrib import admin
from django.contrib.auth import get_user_model
from django.utils.html import format_html
from django.urls import path
from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import JsonResponse
from .models import Notification

User = get_user_model()


class NotificationAdmin(admin.ModelAdmin):
    list_display = ['user', 'notification_type', 'message_preview', 'is_read', 'created_at']
    list_filter = ['notification_type', 'is_read', 'created_at']
    search_fields = ['user__username', 'user__email', 'message']
    readonly_fields = ['created_at']
    date_hierarchy = 'created_at'
    actions = ['mark_as_read', 'mark_as_unread']
    
    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['send_notification_url'] = 'admin:notifications_notification_send'
        return super().changelist_view(request, extra_context=extra_context)
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('send-notification/', self.admin_site.admin_view(self.send_notification_view), name='notifications_notification_send'),
        ]
        return custom_urls + urls
    
    def send_notification_view(self, request):
        """Custom admin view to send notifications to users"""
        if request.method == 'POST':
            recipient_type = request.POST.get('recipient_type', 'selected')
            selected_users = request.POST.getlist('selected_users')
            message = request.POST.get('message', '').strip()
            notification_type = request.POST.get('notification_type', 'platform')
            link = request.POST.get('link', '').strip()
            
            if not message:
                messages.error(request, 'Please enter a notification message.')
            else:
                try:
                    users_to_notify = []
                    
                    if recipient_type == 'all':
                        # Send to all users
                        users_to_notify = User.objects.all()
                    elif recipient_type == 'selected' and selected_users:
                        # Send to selected users
                        users_to_notify = User.objects.filter(pk__in=selected_users)
                    else:
                        messages.error(request, 'Please select at least one user or choose "All Users".')
                        return redirect('admin:notifications_notification_send')
                    
                    count = 0
                    for user in users_to_notify:
                        Notification.create_notification(
                            user=user,
                            message=message,
                            notification_type=notification_type,
                            link=link if link else None
                        )
                        count += 1
                    
                    messages.success(request, f'Notification sent to {count} user(s)!')
                    
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return JsonResponse({
                            'success': True,
                            'message': f'Notification sent to {count} user(s)'
                        })
                except Exception as e:
                    messages.error(request, f'Error sending notification: {str(e)}')
            
            return redirect('admin:notifications_notification_send')
        
        # Get all users for selection
        users = User.objects.all().order_by('username')
        total_users = users.count()
        
        context = {
            'title': 'Send Notification',
            'users': users,
            'total_users': total_users,
            'notification_types': Notification.NOTIFICATION_TYPES,
            'opts': self.model._meta,
            'has_view_permission': True,
        }
        return render(request, 'admin/notifications/send_notification.html', context)
    
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
