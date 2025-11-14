from django.urls import path
from . import views

app_name = 'vouchers'

urlpatterns = [
    path('', views.my_vouchers, name='my_vouchers'),
    path('json/', views.my_vouchers_json, name='my_vouchers_json'),
    path('<int:voucher_id>/', views.voucher_detail, name='voucher_detail'),
    path('<int:voucher_id>/json/', views.voucher_detail_json, name='voucher_detail_json'),
]

