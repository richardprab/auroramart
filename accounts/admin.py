from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import (
    User,
    Address,
    Wishlist,
    SaleSubscription,
    BrowsingHistory,
)
from notifications.models import Notification


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """
    Customizes the User display in the admin panel.
    """

    list_display = ("username", "email", "first_name", "last_name", "is_staff")
    list_filter = ("is_staff", "is_active", "gender", "employment_status")
    search_fields = ("username", "email", "first_name", "last_name")
    fieldsets = BaseUserAdmin.fieldsets + (
        (
            "Demographic Information",
            {
                "fields": (
                    "age",
                    "gender",
                    "employment_status",
                    "occupation",
                    "education",
                    "household_size",
                    "has_children",
                    "monthly_income_sgd",
                ),
            },
        ),
        (
            "Profile Details",
            {
                "fields": (
                    "phone",
                    "avatar",
                ),
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


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    """
    Customizes the Notification display in the admin panel.
    """

    list_display = ["user", "notification_type", "message", "is_read", "created_at"]
    list_filter = ["notification_type", "is_read", "created_at"]
    search_fields = ["user__username", "message"]
    date_hierarchy = "created_at"
