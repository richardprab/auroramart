from django.contrib import admin
from .models import Order, OrderItem

class OrderItemInline(admin.TabularInline):
    """
    Allows editing OrderItems directly within the Order admin page.
    """
    model = OrderItem
    extra = 0
    readonly_fields = ('product_variant', 'quantity', 'price')

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    """
    Customizes the Order display in the admin panel.
    """
    list_display = ('order_number', 'user', 'total', 'status', 'payment_status', 'created_at')
    list_filter = ('status', 'payment_status', 'created_at')
    search_fields = ('order_number', 'user__username', 'contact_number', 'delivery_address')
    inlines = [OrderItemInline]
    readonly_fields = (
        'order_number', 'user', 'total', 'created_at', 'updated_at', 'expected_delivery_date'
    )
    
    fieldsets = (
        ('Order Information', {
            'fields': ('user', 'status', 'payment_status', 'total', 'tracking_number')
        }),
        ('Delivery Details', {
            'fields': ('address', 'contact_number', 'delivery_address', 'current_location', 'expected_delivery_date')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )
