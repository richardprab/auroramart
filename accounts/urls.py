from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = "accounts"

urlpatterns = [
    # Auth
    path("register/", views.register, name="register"),
    path(
        "login/",
        auth_views.LoginView.as_view(template_name="accounts/login.html"),
        name="login",
    ),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    # Profile
    path("profile/", views.profile, name="profile"),
    # Wishlist
    path("wishlist/", views.wishlist, name="wishlist"),
    path(
        "wishlist/add/<int:product_id>/",
        views.add_to_wishlist,
        name="add_to_wishlist",
    ),
    path(
        "wishlist/remove/<int:product_id>/",
        views.remove_from_wishlist,
        name="remove_from_wishlist",
    ),
]
