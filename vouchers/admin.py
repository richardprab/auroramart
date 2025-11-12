from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import Voucher, VoucherUsage


class VoucherUsageInline(admin.TabularInline):
    """Inline admin for voucher usage tracking"""
    model = VoucherUsage
    extra = 0
    readonly_fields = ('user', 'order', 'discount_amount', 'used_at')
    can_delete = False
    
    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Voucher)
class VoucherAdmin(admin.ModelAdmin):
    """
    Enhanced admin interface for voucher management.
    """
    list_display = (
        'promo_code', 'name', 'discount_type', 'discount_display', 
        'usage_status', 'is_active', 'validity_status', 'created_at'
    )
    list_filter = (
        'is_active', 'discount_type', 'first_time_only', 
        'exclude_sale_items', 'start_date', 'end_date', 'created_at'
    )
    search_fields = ('name', 'promo_code', 'description')
    list_display_links = ('promo_code', 'name')
    readonly_fields = ('current_uses', 'created_at', 'updated_at')
    filter_horizontal = ('applicable_categories', 'applicable_products')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'promo_code', 'description', 'is_active')
        }),
        ('Discount Configuration', {
            'fields': (
                'discount_type', 'discount_value', 'max_discount',
            ),
            'description': 'Configure how the discount is applied.'
        }),
        ('Eligibility Requirements', {
            'fields': (
                'min_purchase', 'first_time_only', 'exclude_sale_items',
                'applicable_categories', 'applicable_products', 'user'
            ),
            'description': 'Set requirements for voucher usage.'
        }),
        ('Usage Limits', {
            'fields': (
                'max_uses', 'max_uses_per_user', 'current_uses'
            ),
            'description': 'Control how many times the voucher can be used.'
        }),
        ('Validity Period', {
            'fields': ('start_date', 'end_date'),
            'description': 'Set when the voucher is valid.'
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    inlines = [VoucherUsageInline]
    
    def discount_display(self, obj):
        """Display discount in a readable format"""
        if obj.discount_type == 'percent':
            display = f"{obj.discount_value}%"
            if obj.max_discount:
                display += f" (max ${obj.max_discount})"
            return display
        elif obj.discount_type == 'fixed':
            return f"${obj.discount_value}"
        elif obj.discount_type == 'free_shipping':
            return "Free Shipping"
        return "-"
    discount_display.short_description = "Discount"
    
    def usage_status(self, obj):
        """Show usage statistics"""
        if obj.max_uses:
            percentage = (obj.current_uses / obj.max_uses) * 100
            color = 'green' if percentage < 80 else 'orange' if percentage < 100 else 'red'
            return format_html(
                '<span style="color: {};">{}/{} uses</span>',
                color, obj.current_uses, obj.max_uses
            )
        return f"{obj.current_uses} uses (unlimited)"
    usage_status.short_description = "Usage"
    
    def validity_status(self, obj):
        """Show validity status with color coding"""
        from django.utils import timezone
        now = timezone.now()
        
        if not obj.is_active:
            return format_html('<span style="color: red;">Inactive</span>')
        elif now < obj.start_date:
            return format_html('<span style="color: orange;">Not Started</span>')
        elif now > obj.end_date:
            return format_html('<span style="color: red;">Expired</span>')
        else:
            return format_html('<span style="color: green;">Valid</span>')
    validity_status.short_description = "Status"
    
    def save_model(self, request, obj, form, change):
        """Set created_by when creating a new voucher"""
        if not change:  # New object
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(VoucherUsage)
class VoucherUsageAdmin(admin.ModelAdmin):
    """
    Admin interface for viewing voucher usage history.
    """
    list_display = ('voucher', 'user', 'order_link', 'discount_amount', 'used_at')
    list_filter = ('used_at', 'voucher')
    search_fields = ('voucher__promo_code', 'user__username', 'user__email', 'order__order_number')
    readonly_fields = ('voucher', 'user', 'order', 'discount_amount', 'used_at')
    date_hierarchy = 'used_at'
    
    def order_link(self, obj):
        """Link to order detail"""
        if obj.order:
            url = reverse('admin:orders_order_change', args=[obj.order.pk])
            return format_html('<a href="{}">{}</a>', url, obj.order.order_number)
        return "-"
    order_link.short_description = "Order"
    
    def has_add_permission(self, request):
        return False  # Voucher usage is created automatically
    
    def has_change_permission(self, request, obj=None):
        return False  # Voucher usage is read-only

