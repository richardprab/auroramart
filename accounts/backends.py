"""
Custom authentication backend to support Customer, Staff, and Superuser models.
Since AUTH_USER_MODEL is set to User but we have multiple user types (Customer, Staff, Superuser),
we need to check all three models during authentication.
"""
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from .models import Customer, Staff, Superuser


class MultiUserModelBackend(ModelBackend):
    """
    Custom authentication backend that supports Customer, Staff, and Superuser.
    All three extend User via multi-table inheritance, so we check each model type.
    """
    
    def authenticate(self, request, username=None, password=None, **kwargs):
        # Try Customer first (most common user type)
        try:
            user = Customer.objects.get(username=username)
            if user.check_password(password) and self.user_can_authenticate(user):
                return user
        except Customer.DoesNotExist:
            pass
        
        # Try Staff
        try:
            user = Staff.objects.get(username=username)
            if user.check_password(password) and self.user_can_authenticate(user):
                return user
        except Staff.DoesNotExist:
            pass
        
        # Try Superuser
        try:
            user = Superuser.objects.get(username=username)
            if user.check_password(password) and self.user_can_authenticate(user):
                return user
        except Superuser.DoesNotExist:
            pass
        
        # Fallback: Try User model directly (in case there are User instances without child models)
        UserModel = get_user_model()  # This will be User
        try:
            user = UserModel.objects.get(username=username)
            if user.check_password(password) and self.user_can_authenticate(user):
                return user
        except UserModel.DoesNotExist:
            pass
        
        return None
    
    def get_user(self, user_id):
        # Try Customer first (most common user type)
        try:
            return Customer.objects.get(pk=user_id)
        except Customer.DoesNotExist:
            pass
        
        # Try Staff
        try:
            return Staff.objects.get(pk=user_id)
        except Staff.DoesNotExist:
            pass
        
        # Try Superuser
        try:
            return Superuser.objects.get(pk=user_id)
        except Superuser.DoesNotExist:
            pass
        
        # Fallback: Try User model directly
        UserModel = get_user_model()  # This will be User
        try:
            return UserModel.objects.get(pk=user_id)
        except UserModel.DoesNotExist:
            pass
        
        return None
