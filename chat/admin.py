from django.contrib import admin
from .models import ChatSession, ChatMessage


class ChatMessageInline(admin.TabularInline):
    model = ChatMessage
    extra = 0
    fields = ['message', 'is_from_admin', 'is_read', 'created_at']
    readonly_fields = ['created_at']
    
    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'title', 'created_at', 'updated_at', 'is_active', 'unread_count']
    list_filter = ['is_active', 'created_at']
    search_fields = ['user__username', 'user__email', 'title']
    readonly_fields = ['created_at', 'updated_at', 'unread_count']
    inlines = [ChatMessageInline]
    
    fieldsets = (
        ('Session Info', {
            'fields': ('user', 'title', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'unread_count')
        }),
    )
    
    def unread_count(self, obj):
        return obj.messages.filter(is_read=False, is_from_admin=False).count()
    unread_count.short_description = 'Unread from User'


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ['id', 'session', 'get_sender', 'message_preview', 'is_read', 'created_at']
    list_filter = ['is_from_admin', 'is_read', 'created_at']
    search_fields = ['message', 'session__user__username']
    readonly_fields = ['created_at']
    
    fieldsets = (
        ('Message Info', {
            'fields': ('session', 'message', 'is_from_admin', 'is_read')
        }),
        ('Timestamp', {
            'fields': ('created_at',)
        }),
    )
    
    def get_sender(self, obj):
        return "Admin" if obj.is_from_admin else obj.session.user.username
    get_sender.short_description = 'Sender'
    
    def message_preview(self, obj):
        return obj.message[:50] + '...' if len(obj.message) > 50 else obj.message
    message_preview.short_description = 'Message'
