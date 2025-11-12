from django.contrib import admin
from .models import HomepageBanner

@admin.register(HomepageBanner)
class HomepageBannerAdmin(admin.ModelAdmin):
    """
    Customizes the HomepageBanner display in the admin panel.
    """
    list_display = ('title', 'link', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('title', 'message')
