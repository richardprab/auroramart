from django.urls import path
from . import views

app_name = 'orders'

urlpatterns = [
    path('checkout/', views.checkout, name='checkout'),
    path('checkout/process/', views.process_checkout, name='process_checkout'),
    path('checkout/apply-voucher/', views.apply_voucher, name='apply_voucher'),
    path('checkout/remove-voucher/', views.remove_voucher, name='remove_voucher'),
    path('checkout/available-vouchers/', views.get_available_vouchers, name='get_available_vouchers'),
    path('checkout/create-stripe-checkout/', views.create_stripe_checkout, name='create_stripe_checkout'),
    path('payment/success/', views.payment_success, name='payment_success'),
    path('payment/cancel/', views.payment_cancel, name='payment_cancel'),
    path('webhooks/stripe/', views.stripe_webhook, name='stripe_webhook'),
    path('my-orders/', views.order_list, name='order_list'),
    path('order/<int:order_id>/', views.order_detail, name='order_detail'),
    path('order/<int:order_id>/cancel/', views.cancel_order, name='cancel_order'),
]
