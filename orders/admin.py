from django.contrib import admin
from .models import Order, OrderItem

class OrderItemInline(admin.TabularInline):
    """
    Allows editing OrderItems directly within the Order admin page.
    """
    model = OrderItem
    extra = 0
    readonly_fields = ('variant', 'quantity', 'price')  # Changed 'product_variant' to 'variant'

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    """
    Customizes the Order display in the admin panel.
    """
    list_display = ('order_number', 'user', 'total_amount', 'status', 'payment_status', 'created_at')  # Changed 'order_number' to 'id', 'total' to 'total_amount'
    list_filter = ('status', 'payment_status', 'created_at')
    search_fields = ('order_number', 'user__username', 'contact_number', 'delivery_address')  # Changed to fields that exist
    inlines = [OrderItemInline]
    readonly_fields = (
        'order_number', 'user', 'total_amount', 'created_at', 'updated_at', 'expected_delivery_date'
    )  # Only keep fields that exist in the Order model
    
    fieldsets = (
        ('Order Information', {
            'fields': ('user', 'status', 'payment_status', 'total_amount', 'tracking_number')
        }),
        ('Delivery Details', {
            'fields': ('address', 'contact_number', 'delivery_address', 'current_location', 'expected_delivery_date')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )
