from django.urls import path
from django.contrib.auth.views import (
    LoginView, LogoutView,
    PasswordResetView, PasswordResetDoneView,
    PasswordResetConfirmView, PasswordResetCompleteView
)
from . import views
from .forms import CustomerPasswordResetForm

app_name = "accounts"

urlpatterns = [
    path("register/", views.register, name="register"),
    path('login/', views.user_login, name='login'),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("profile/", views.profile, name="profile"),
    path("profile/update-demographics/", views.update_demographics, name="update_demographics"),
    path("profile/change-password/", views.change_password, name="change_password"),
    path("addresses/", views.addresses, name="addresses"),
    path("addresses/add/", views.add_address, name="add_address"),
    path("addresses/<int:address_id>/edit/", views.edit_address, name="edit_address"),
    path("addresses/<int:address_id>/delete/", views.delete_address, name="delete_address"),
    path("addresses/<int:address_id>/set-default/", views.set_default_address, name="set_default_address"),
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
    
    # Password reset URLs
    path("password-reset/", PasswordResetView.as_view(
        template_name='accounts/password_reset.html',
        email_template_name='accounts/password_reset_email.html',
        subject_template_name='accounts/password_reset_subject.txt',
        success_url='/accounts/password-reset/done/',
        form_class=CustomerPasswordResetForm
    ), name='password_reset'),
    path("password-reset/done/", PasswordResetDoneView.as_view(
        template_name='accounts/password_reset_done.html'
    ), name='password_reset_done'),
    path("password-reset-confirm/<uidb64>/<token>/", PasswordResetConfirmView.as_view(
        template_name='accounts/password_reset_confirm.html',
        success_url='/accounts/password-reset/complete/'
    ), name='password_reset_confirm'),
    path("password-reset/complete/", PasswordResetCompleteView.as_view(
        template_name='accounts/password_reset_complete.html'
    ), name='password_reset_complete'),
    
    # AJAX endpoints (JSON responses)
    path("ajax/wishlist/count/", views.get_wishlist_count, name="ajax_wishlist_count"),
    # # COMMENTED OUT: Preferred category is redundant - ML model should be primary
    # path("ajax/shopping-interest/", views.update_shopping_interest, name="update_shopping_interest"),
]
