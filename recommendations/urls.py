from django.urls import path
from . import api_views

app_name = 'recommendations'

urlpatterns = [
    path('api/predict-category/', api_views.predict_user_category, name='predict_category'),
    path('api/similar/<int:product_id>/', api_views.get_similar_products, name='similar_products'),
    path('api/cart-recommendations/', api_views.get_cart_recommendations, name='cart_recommendations'),
    path('api/personalized/', api_views.get_personalized_recommendations, name='personalized'),
]
