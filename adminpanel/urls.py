from django.urls import path
from . import views

app_name = 'adminpanel'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('products/', views.product_management, name='products'),
    path('products/<int:product_id>/edit/', views.edit_product, name='edit_product'),
    path('customer-support/', views.customer_support, name='customer_support'),
    path('customer-support/<int:conversation_id>/', views.chat_conversation, name='chat_conversation'),
    path('analytics/', views.analytics, name='analytics'),
]