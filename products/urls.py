from django.urls import path
from . import views

app_name = "products"

urlpatterns = [
    path("", views.product_list, name="product_list"),
    path("category/<slug:slug>/", views.category_list, name="category_list"),
    path("search/", views.search, name="search"),
    path("search-suggestions/", views.search_suggestions, name="search_suggestions"),
    path("ajax/<int:product_id>/", views.product_detail_ajax, name="product_detail_ajax"),
    path("<str:sku>/review/", views.submit_review, name="submit_review"),
    path("review/<int:review_id>/delete/", views.delete_review, name="delete_review"),
    path("<str:sku>/reviews/", views.get_reviews_ajax, name="get_reviews_ajax"),
    path("<str:sku>/", views.product_detail, name="product_detail"),
]
