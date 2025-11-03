from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import (
    User,
    Address,
    Wishlist,
    SaleSubscription,
    BrowsingHistory,
    ChatConversation,
    ChatMessage,
)
from notifications.models import Notification


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """
    Customizes the User display in the admin panel.
    """

    list_display = ("username", "email", "first_name", "last_name", "role", "is_staff")
    list_filter = ("role", "is_staff", "is_active")
    search_fields = ("username", "email", "first_name", "last_name")
    fieldsets = BaseUserAdmin.fieldsets + (
        (
            "Account Details",
            {
                "fields": (
                    "role",
                    "age_range",
                    "gender",
                    "employment",
                    "income_range",
                    "preferred_category",
                    "phone",
                    "date_of_birth",
                    "avatar",
                ),
            },
        ),
        (
            "Notification Toggles",
            {
                "fields": ("allow_marketing_emails", "allow_sale_notifications"),
            },
        ),
    )


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    """
    Customizes the Address display in the admin panel.
    """

    list_display = ("user", "full_name", "address_type", "city", "state", "is_default")
    list_filter = ("is_default", "country")
    search_fields = ("user__username", "full_name", "city", "state", "zip_code")


@admin.register(Wishlist)
class WishlistAdmin(admin.ModelAdmin):
    """
    Customizes the Wishlist display in the admin panel.
    """

    list_display = ("user", "product_variant", "created_at")
    search_fields = ("user__username", "product_variant__sku")


@admin.register(SaleSubscription)
class SaleSubscriptionAdmin(admin.ModelAdmin):
    """
    Customizes the SaleSubscription display in the admin panel.
    """

    list_display = ("user", "product_variant", "created_at")
    search_fields = ("user__username", "product_variant__sku")


@admin.register(BrowsingHistory)
class BrowsingHistoryAdmin(admin.ModelAdmin):
    """
    Customizes the BrowsingHistory display in the admin panel.
    """

    list_display = ("user", "product", "viewed_at")
    search_fields = ("user__username", "product__name")
    list_filter = ("viewed_at",)


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
        "subject",              # ADD THIS
        "message_type",         # ADD THIS
        "status",           # ADD THIS
        "product",
        "admin",
        "user_has_unread",
        "admin_has_unread",
        "created_at",
    )
    list_filter = ("user_has_unread", "admin_has_unread")
    search_fields = ("user__username", "product__name", "admin__username")
    inlines = [ChatMessageInline]
    readonly_fields = ("created_at", "updated_at")  # ADD updated_at


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    """
    Customizes the Notification display in the admin panel.
    """

    list_display = ["user", "notification_type", "message", "is_read", "created_at"]
    list_filter = ["notification_type", "is_read", "created_at"]
    search_fields = ["user__username", "message"]
    date_hierarchy = "created_at"
