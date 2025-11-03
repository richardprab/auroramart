"""
URL configuration for auroramart project.
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),
    
    # API endpoints
    path("api/", include("auroramartproject.api_urls")),
    path("", include("home.urls")),
    path("accounts/", include("accounts.urls")),
    path("adminpanel/", include("adminpanel.urls")),
    path("products/", include("products.urls")),
    path("cart/", include("cart.urls")),
    path("orders/", include("orders.urls")),
    path("notifications/", include("notifications.urls")),
    path("chat/", include("chat.urls")),
]

# Serve static and media files during development
if settings.DEBUG:
    urlpatterns += static(
        settings.STATIC_URL, document_root=settings.BASE_DIR / "static"
    )
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
