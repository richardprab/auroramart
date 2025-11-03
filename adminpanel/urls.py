from django.urls import path
from . import views
from django.contrib.auth.views import LogoutView

app_name = 'adminpanel'

urlpatterns = [
    # Dashboard
    path('', views.dashboard, name='dashboard'),
    
    # Customer Assistance
    path('customer-support/', views.customer_support, name='customer_support'),
    path('customer-support/<int:conversation_id>/', views.chat_conversation, name='chat_conversation'),
    
    # Product Management
    path('products/', views.product_management, name='products'),
    path('products/search/', views.search_product, name='search_product'),
    path('products/update/', views.update_product, name='update_product'),
    
    # Order Management
    path('orders/', views.order_management, name='order_management'),
    path('orders/update/<int:order_id>/', views.update_order, name='update_order'),
    
    # Analytics
    path('analytics/', views.analytics, name='analytics'),

    # Logout
    path("logout/", LogoutView.as_view(), name="logout"),
]