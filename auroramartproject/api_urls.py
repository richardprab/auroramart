"""
API URL Configuration for AuroraMart
Centralized routing for all API endpoints
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

# Import ViewSets
from products.api_views import (
    CategoryViewSet,
    ProductViewSet,
    ProductVariantViewSet,
    ReviewViewSet,
)
from cart.api_views import CartViewSet
from accounts.api_views import (
    UserRegistrationView,
    UserProfileView,
    AddressViewSet,
    WishlistViewSet,
    SaleSubscriptionViewSet,
    BrowsingHistoryViewSet,
    ChatConversationViewSet,
)
from orders.api_views import OrderViewSet
from notifications.api_views import NotificationViewSet
from recommendations import api_views as recommendations_api

# Create router
router = DefaultRouter()

# Register product routes
router.register(r'categories', CategoryViewSet, basename='category')
router.register(r'products', ProductViewSet, basename='product')
router.register(r'variants', ProductVariantViewSet, basename='variant')
router.register(r'reviews', ReviewViewSet, basename='review')

# Register cart routes
router.register(r'cart', CartViewSet, basename='cart')

# Register account routes
router.register(r'addresses', AddressViewSet, basename='address')
router.register(r'wishlist', WishlistViewSet, basename='wishlist')
router.register(r'sale-subscriptions', SaleSubscriptionViewSet, basename='sale-subscription')
router.register(r'browsing-history', BrowsingHistoryViewSet, basename='browsing-history')
router.register(r'conversations', ChatConversationViewSet, basename='conversation')

# Register order routes
router.register(r'orders', OrderViewSet, basename='order')

# Register notification routes
router.register(r'notifications', NotificationViewSet, basename='notification')

urlpatterns = [
    # User registration and profile
    path('auth/register/', UserRegistrationView.as_view(), name='register'),
    path('auth/profile/', UserProfileView.as_view(), name='profile'),
    
    # Recommendations API
    path('recommendations/predict-category/', recommendations_api.predict_user_category, name='predict_category'),
    path('recommendations/similar-products/<int:product_id>/', recommendations_api.get_similar_products, name='similar_products'),
    path('recommendations/cart-recommendations/', recommendations_api.get_cart_recommendations, name='cart_recommendations'),
    path('recommendations/personalized/', recommendations_api.get_personalized_recommendations, name='personalized'),
    
    # Include router URLs
    path('', include(router.urls)),
]
