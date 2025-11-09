from django.urls import path
from . import views

app_name = "products"

urlpatterns = [
    path("", views.product_list, name="product_list"),
    path("category/<slug:slug>/", views.category_list, name="category_list"),
    path("search/", views.search, name="search"),
    path("ajax/<int:product_id>/", views.product_detail_ajax, name="product_detail_ajax"),
    path("<slug:slug>/", views.product_detail, name="product_detail"),
]
