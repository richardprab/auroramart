from django.contrib import admin
from .models import (
    Category, Product, ProductImage, Review, ProductVariant
)

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    """
    Customizes the Category display in the admin panel.
    """
    list_display = ('name', 'slug', 'parent', 'is_active')
    list_filter = ('is_active', 'parent')
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)} # Auto-fills slug from name

class ProductImageInline(admin.TabularInline):
    """
    Allows editing ProductImages directly within the Product admin page.
    """
    model = ProductImage
    extra = 1 # Show one extra form for new images

@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    """
    Customizes the ProductVariant display in the admin panel.
    """
    list_display = ('sku', 'product', 'price', 'compare_price', 'stock', 'is_active')
    list_filter = ('is_active', 'product__category')
    search_fields = ('sku', 'product__name')

class ProductVariantInline(admin.TabularInline):
    """
    Allows editing ProductVariants directly within the Product admin page.
    """
    model = ProductVariant
    extra = 1
    show_change_link = True # Allows clicking to the variant's own admin page

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    """
    Customizes the Product display in the admin panel.
    """
    list_display = ('name', 'sku', 'category', 'rating', 'reorder_quantity', 'is_active')
    list_filter = ('is_active', 'category')
    search_fields = ('name', 'sku', 'category__name')
    prepopulated_fields = {'slug': ('name',)}
    inlines = [ProductImageInline, ProductVariantInline]

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    """
    Customizes the Review display in the admin panel.
    """
    list_display = ('product', 'user', 'rating', 'created_at')
    list_filter = ('rating', 'created_at')
    search_fields = ('product__name', 'user__username', 'title', 'comment')
    readonly_fields = ('created_at', 'updated_at')

