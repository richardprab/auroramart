from django.contrib import admin
from .models import ChatConversation, ChatMessage


class ChatMessageInline(admin.TabularInline):
    """
    Allows editing ChatMessages directly within the ChatConversation admin page.
    """

    model = ChatMessage
    extra = 0  # Don't show extra empty forms
    readonly_fields = ("sender", "content", "created_at")


@admin.register(ChatConversation)
class ChatConversationAdmin(admin.ModelAdmin):
    """
    Customizes the ChatConversation display in the admin panel.
    """

    list_display = (
        "user",
        "subject",
        "message_type",
        "status",
        "product",
        "admin",
        "user_has_unread",
        "admin_has_unread",
        "created_at",
    )
    list_filter = ("user_has_unread", "admin_has_unread")
    search_fields = ("user__username", "product__name", "admin__username")
    inlines = [ChatMessageInline]
    readonly_fields = ("created_at", "updated_at")


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    """
    Customizes the ChatMessage display in the admin panel.
    """

    list_display = ("conversation", "sender", "content", "created_at")
    list_filter = ("created_at",)
    search_fields = ("content", "sender__username", "conversation__subject")
    readonly_fields = ("created_at",)
