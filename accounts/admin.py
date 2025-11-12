from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from django.urls import reverse
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
from vouchers.models import Voucher


class UserVoucherInline(admin.TabularInline):
    """Inline admin for viewing/assigning vouchers to users"""
    model = Voucher
    fk_name = 'user'
    extra = 1
    fields = ('promo_code', 'name', 'discount_type', 'discount_value', 'is_active', 'start_date', 'end_date')
    verbose_name = "Assigned Voucher"
    verbose_name_plural = "User-Specific Vouchers"
    
    def get_queryset(self, request):
        """Only show vouchers assigned to this user"""
        qs = super().get_queryset(request)
        if hasattr(qs, 'filter'):
            return qs.filter(user__isnull=False)
        return qs


# User is now abstract, so we can't register it in admin
# Use CustomerAdmin, StaffAdmin, and SuperuserAdmin instead


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    """
    Admin interface for Customer model with demographic fields.
    """
    
    list_display = ("username", "email", "first_name", "last_name", "age", "gender", "employment_status", "voucher_count")
    list_filter = ("gender", "employment_status", "occupation", "education", "has_children")
    search_fields = ("username", "email", "first_name", "last_name")
    inlines = [UserVoucherInline]
    
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
    
    def voucher_count(self, obj):
        """Display count of vouchers assigned to this user"""
        count = Voucher.objects.filter(user=obj).count()
        if count > 0:
            url = reverse('admin:vouchers_voucher_changelist') + f'?user__id__exact={obj.id}'
            return format_html('<a href="{}">{} voucher{}</a>', url, count, 's' if count != 1 else '')
        return "0 vouchers"
    voucher_count.short_description = "Vouchers"
    
    actions = ['assign_voucher_to_users']
    
    def assign_voucher_to_users(self, request, queryset):
        """Admin action to assign a voucher to selected users"""
        from django.http import HttpResponseRedirect
        from django.urls import reverse
        
        # Get voucher IDs from POST data
        voucher_id = request.POST.get('voucher_id')
        if not voucher_id:
            # Show voucher selection page
            vouchers = Voucher.objects.filter(user__isnull=True, is_active=True).order_by('promo_code')
            if not vouchers.exists():
                self.message_user(request, "No public vouchers available. Please create a voucher first.", level='error')
                return
            
            from django.template.response import TemplateResponse
            context = {
                'users': queryset,
                'vouchers': vouchers,
                'opts': self.model._meta,
                'action_checkbox_name': admin.helpers.ACTION_CHECKBOX_NAME,
            }
            return TemplateResponse(request, 'admin/accounts/customer/assign_voucher.html', context)
        
        # Assign voucher to selected users
        try:
            voucher = Voucher.objects.get(id=voucher_id)
            assigned_count = 0
            
            for user in queryset:
                # Create a user-specific copy of the voucher
                user_voucher = Voucher.objects.create(
                    name=f"{voucher.name} - {user.username}",
                    promo_code=f"{voucher.promo_code}-{user.id}",
                    description=voucher.description,
                    discount_type=voucher.discount_type,
                    discount_value=voucher.discount_value,
                    max_discount=voucher.max_discount,
                    min_purchase=voucher.min_purchase,
                    first_time_only=voucher.first_time_only,
                    exclude_sale_items=voucher.exclude_sale_items,
                    max_uses=voucher.max_uses,
                    max_uses_per_user=voucher.max_uses_per_user,
                    start_date=voucher.start_date,
                    end_date=voucher.end_date,
                    is_active=voucher.is_active,
                    user=user,
                    created_by=request.user,
                )
                assigned_count += 1
            
            self.message_user(
                request,
                f"Successfully assigned voucher '{voucher.promo_code}' to {assigned_count} user(s).",
                level='success'
            )
        except Voucher.DoesNotExist:
            self.message_user(request, "Voucher not found.", level='error')
        except Exception as e:
            self.message_user(request, f"Error assigning voucher: {str(e)}", level='error')
    
    assign_voucher_to_users.short_description = "Assign voucher to selected users"


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
