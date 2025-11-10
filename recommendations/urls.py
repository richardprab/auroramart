from django.urls import path
from . import views

app_name = 'recommendations'

urlpatterns = [
    path('predict-category/', views.predict_user_category, name='predict_category'),
    path('similar-products/<int:product_id>/', views.get_similar_products, name='similar_products'),
    path('cart-recommendations/', views.get_cart_recommendations, name='cart_recommendations'),
    path('personalized/', views.get_personalized_recommendations, name='personalized'),
]
