from django.urls import path
from django.contrib.auth.views import LoginView, LogoutView
from . import views

app_name = "accounts"

urlpatterns = [
    path("register/", views.register, name="register"),
    path("welcome/", views.welcome_personalization, name="welcome"),
    path('login/', views.user_login, name='login'),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("profile/", views.profile, name="profile"),
    path("profile/update-demographics/", views.update_demographics, name="update_demographics"),
    path("wishlist/", views.wishlist, name="wishlist"),
    path(
        "wishlist/add/<int:product_id>/", views.add_to_wishlist, name="add_to_wishlist"
    ),
    path(
        "wishlist/remove/<int:product_id>/",
        views.remove_from_wishlist,
        name="remove_from_wishlist",
    ),
    path(
        "wishlist/move-to-cart/<int:wishlist_id>/",
        views.move_to_cart,
        name="move_to_cart",
    ),
]
