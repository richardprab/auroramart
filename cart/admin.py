from django.contrib import admin
from .models import Cart, CartItem

class CartItemInline(admin.TabularInline):
    """
    Allows editing CartItems directly within the Cart admin page.
    """
    model = CartItem
    extra = 0 # Don't show extra empty forms
    readonly_fields = ('product_variant', 'quantity', 'added_at')

@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    """
    Customizes the Cart display in the admin panel.
    """
    list_display = ('id', 'user', 'session_key', 'created_at', 'updated_at')
    list_filter = ('created_at',)
    search_fields = ('user__username', 'session_key')
    inlines = [CartItemInline]
    readonly_fields = ('created_at', 'updated_at')
