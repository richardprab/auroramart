from django.contrib import admin
from .models import Category, Product, ProductImage, Review


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "parent", "created_at"]
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ["name"]


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "category",
        "price",
        "stock",
        "rating",
        "is_trending",
        "is_bestseller",
        "is_active",
    ]
    list_filter = [
        "category",
        "is_trending",
        "is_bestseller",
        "is_featured",
        "is_active",
        "created_at",
    ]
    search_fields = ["name", "description", "sku"]
    prepopulated_fields = {"slug": ("name",)}
    list_editable = ["price", "stock", "is_trending", "is_bestseller", "is_active"]
    inlines = [ProductImageInline]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ["product", "is_primary", "order", "created_at"]
    list_filter = ["is_primary"]


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ["product", "user", "rating", "is_verified_purchase", "created_at"]
    list_filter = ["rating", "is_verified_purchase", "created_at"]
    search_fields = ["product__name", "user__username", "title", "comment"]
    readonly_fields = ["created_at", "updated_at"]
