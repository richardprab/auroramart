from django.contrib import admin
from .models import HomepageBanner, Coupon

@admin.register(HomepageBanner)
class HomepageBannerAdmin(admin.ModelAdmin):
    """
    Customizes the HomepageBanner display in the admin panel.
    """
    list_display = ('title', 'link', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('title', 'message')

@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    """
    Customizes the Coupon display in the admin panel.
    """
    list_display = ('name', 'promo_code', 'discount_type', 'discount_value', 'is_active', 'start_date', 'end_date')
    list_filter = ('is_active', 'discount_type', 'start_date', 'end_date')
    search_fields = ('name', 'promo_code')
    list_display_links = ('name', 'promo_code')
