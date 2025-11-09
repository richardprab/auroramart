from django.urls import path
from . import api_views

app_name = 'recommendations'

urlpatterns = [
    path('predict-category/', api_views.predict_user_category, name='predict_category'),
    path('similar/<int:product_id>/', api_views.get_similar_products, name='similar_products'),
    path('cart-recommendations/', api_views.get_cart_recommendations, name='cart_recommendations'),
    path('personalized/', api_views.get_personalized_recommendations, name='personalized'),
]
