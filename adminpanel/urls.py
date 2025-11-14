from django.urls import path
from . import views
from django.contrib.auth.views import LogoutView

app_name = 'adminpanel'

urlpatterns = [
    # Staff Login
    path('login/', views.staff_login, name='staff_login'),
    
    # Dashboard
    path('', views.dashboard, name='dashboard'),
    
    path('customer-support/', views.customer_support, name='customer_support'),
    path('customer-support/<int:conversation_id>/', views.chat_conversation, name='chat_conversation'),
    
    path('products/', views.product_management, name='products'),
    path('products/search/', views.search_product, name='search_product'),
    path('products/edit/<int:product_id>/', views.edit_product, name='edit_product'),
    path('products/update/', views.update_product, name='update_product'),
    
    path('orders/', views.order_management, name='order_management'),
    path('orders/search/', views.search_order, name='search_order'),
    path('orders/edit/<int:order_id>/', views.edit_order, name='edit_order'),
    path('orders/update/<int:order_id>/', views.update_order, name='update_order'),
    
    path('analytics/', views.analytics, name='analytics'),
    
    path('vouchers/', views.voucher_management, name='voucher_management'),
    path('vouchers/add/', views.add_voucher, name='add_voucher'),
    path('vouchers/edit/<int:voucher_id>/', views.edit_voucher, name='edit_voucher'),
    path('vouchers/delete/<int:voucher_id>/', views.delete_voucher, name='delete_voucher'),
    
    path('database/', views.database_management, name='database_management'),
    path('database/run/', views.run_populate_db, name='run_populate_db'),

    # Logout
    path("logout/", LogoutView.as_view(), name="logout"),
]