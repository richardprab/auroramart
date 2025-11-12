from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import (
    User,
    Customer,
    Staff,
    Superuser,
    Address,
    Wishlist,
    SaleSubscription,
    BrowsingHistory,
)
from notifications.models import Notification


# User is now abstract, so we can't register it in admin
# Use CustomerAdmin, StaffAdmin, and SuperuserAdmin instead


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    """
    Admin interface for Customer model with demographic fields.
    """
    
    list_display = ("username", "email", "first_name", "last_name", "age", "gender", "employment_status")
    list_filter = ("gender", "employment_status", "occupation", "education", "has_children")
    search_fields = ("username", "email", "first_name", "last_name")
    
    fieldsets = (
        (
            "User Information",
            {
                "fields": (
                    "username",
                    "email",
                    "first_name",
                    "last_name",
                    "phone",
                    "avatar",
                ),
            },
        ),
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
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                ),
            },
        ),
        (
            "Important dates",
            {
                "fields": ("last_login", "date_joined"),
            },
        ),
    )
    
    readonly_fields = ("last_login", "date_joined")


@admin.register(Superuser)
class SuperuserAdmin(admin.ModelAdmin):
    """
    Admin interface for Superuser proxy model.
    """
    
    list_display = ("username", "email", "first_name", "last_name", "is_active", "last_login")
    list_filter = ("is_active", "date_joined")
    search_fields = ("username", "email", "first_name", "last_name")
    
    fieldsets = (
        (
            "User Information",
            {
                "fields": (
                    "username",
                    "email",
                    "first_name",
                    "last_name",
                ),
            },
        ),
        (
            "Account Status",
            {
                "fields": (
                    "is_active",
                ),
                "description": "Superusers have full admin access. This cannot be changed here.",
            },
        ),
        (
            "Important dates",
            {
                "fields": ("last_login", "date_joined"),
            },
        ),
    )
    
    readonly_fields = ("last_login", "date_joined")
    
    def has_add_permission(self, request):
        """Superusers should be created via createsuperuser command."""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Prevent deletion of superusers from admin."""
        return False


@admin.register(Staff)
class StaffAdmin(admin.ModelAdmin):
    """
    Admin interface for Staff model with permission management.
    """
    
    list_display = ("username", "email", "first_name", "last_name", "permissions", "is_active")
    list_filter = ("permissions", "is_active")
    search_fields = ("username", "email", "first_name", "last_name")
    
    fieldsets = (
        (
            "User Information",
            {
                "fields": (
                    "username",
                    "email",
                    "first_name",
                    "last_name",
                ),
            },
        ),
        (
            "Staff Permissions",
            {
                "fields": (
                    "permissions",
                ),
                "description": "Select which admin panel features this staff member can access. 'All Permissions' grants full access.",
            },
        ),
        (
            "Account Status",
            {
                "fields": (
                    "is_active",
                ),
            },
        ),
        (
            "Important dates",
            {
                "fields": ("last_login", "date_joined"),
            },
        ),
    )
    
    readonly_fields = ("last_login", "date_joined")
    
    def save_model(self, request, obj, form, change):
        """Ensure staff users have is_staff=True"""
        obj.is_staff = True
        obj.is_superuser = False  # Staff are not superusers
        super().save_model(request, obj, form, change)


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
