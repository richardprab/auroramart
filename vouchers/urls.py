from django.urls import path
from . import views

app_name = 'vouchers'

urlpatterns = [
    path('', views.my_vouchers, name='my_vouchers'),
    path('<int:voucher_id>/', views.voucher_detail, name='voucher_detail'),
]

