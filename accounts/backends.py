"""
Custom authentication backend to support Customer, Staff, and Superuser models.
Since AUTH_USER_MODEL is set to Superuser but we have multiple user types,
we need to check all three models during authentication.
"""
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from .models import Customer, Staff


class MultiUserModelBackend(ModelBackend):
    """
    Custom authentication backend that supports Customer, Staff, and Superuser.
    """
    
    def authenticate(self, request, username=None, password=None, **kwargs):
        # Try Superuser first (since it's AUTH_USER_MODEL)
        UserModel = get_user_model()  # This will be Superuser
        try:
            user = UserModel.objects.get(username=username)
            if user.check_password(password) and self.user_can_authenticate(user):
                return user
        except UserModel.DoesNotExist:
            pass
        
        # Try Customer
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
        
        return None
    
    def get_user(self, user_id):
        UserModel = get_user_model()  # This will be Superuser
        
        # Try Superuser first
        try:
            return UserModel.objects.get(pk=user_id)
        except UserModel.DoesNotExist:
            pass
        
        # Try Customer
        try:
            return Customer.objects.get(pk=user_id)
        except Customer.DoesNotExist:
            pass
        
        # Try Staff
        try:
            return Staff.objects.get(pk=user_id)
        except Staff.DoesNotExist:
            pass
        
        return None
