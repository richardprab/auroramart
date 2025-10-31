from django.contrib import admin
from .models import Cart, CartItem


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "user",
        "session_key",
        "get_item_count",
        "get_total",
        "created_at",
    ]
    inlines = [CartItemInline]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ["cart", "product", "quantity", "get_subtotal", "added_at"]
    readonly_fields = ["added_at"]
