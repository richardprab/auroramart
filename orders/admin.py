from django.contrib import admin
from .models import Order, OrderItem

class OrderItemInline(admin.TabularInline):
    """
    Allows editing OrderItems directly within the Order admin page.
    """
    model = OrderItem
    extra = 0
    readonly_fields = ('product_variant', 'quantity', 'price') # Data is historical

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    """
    Customizes the Order display in the admin panel.
    """
    list_display = ('order_number', 'user', 'total', 'status', 'payment_status', 'created_at')
    list_filter = ('status', 'payment_status', 'created_at')
    search_fields = ('order_number', 'user__username', 'shipping_email', 'shipping_full_name')
    inlines = [OrderItemInline]
    readonly_fields = (
        'order_number', 'user', 'subtotal', 'tax', 'shipping_cost', 'total',
        'created_at', 'updated_at', 'paid_at', 'shipped_at', 'delivered_at',
        'shipping_address_link', 'billing_address_link'
    )
