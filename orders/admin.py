from django.contrib import admin
from .models import Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ["product", "quantity", "price", "get_subtotal"]


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = [
        "order_number",
        "user",
        "status",
        "payment_status",
        "total",
        "created_at",
    ]
    list_filter = ["status", "payment_status", "created_at"]
    search_fields = ["order_number", "user__username", "user__email", "shipping_email"]
    inlines = [OrderItemInline]
    readonly_fields = ["order_number", "created_at", "updated_at"]

    fieldsets = (
        (
            "Order Information",
            {
                "fields": (
                    "order_number",
                    "user",
                    "status",
                    "payment_status",
                    "payment_method",
                )
            },
        ),
        ("Pricing", {"fields": ("subtotal", "tax", "shipping_cost", "total")}),
        (
            "Shipping Information",
            {
                "fields": (
                    "shipping_full_name",
                    "shipping_email",
                    "shipping_phone",
                    "shipping_address",
                    "shipping_city",
                    "shipping_state",
                    "shipping_zip",
                    "shipping_country",
                )
            },
        ),
        (
            "Tracking & Notes",
            {"fields": ("tracking_number", "customer_notes", "admin_notes")},
        ),
        (
            "Timestamps",
            {
                "fields": (
                    "created_at",
                    "updated_at",
                    "paid_at",
                    "shipped_at",
                    "delivered_at",
                )
            },
        ),
    )


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ["order", "product", "quantity", "price", "get_subtotal"]
