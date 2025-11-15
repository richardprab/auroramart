"""
Custom authentication backend to support Customer model only.
Only customers can login through the regular login page.
"""
from django.contrib.auth.backends import ModelBackend
from .models import Customer, Staff, Superuser


class MultiUserModelBackend(ModelBackend):
    """
    Custom authentication backend that only supports Customer login.
    Staff and Superuser cannot login through the regular login page.
    
    Supports authentication via username or email (case-insensitive).
    """
    
    def authenticate(self, request, username=None, password=None, **kwargs):
        """
        Authenticate a Customer by username or email.
        This is the Django-standard way to handle authentication.
        """
        if username is None:
            username = kwargs.get('username')
        
        if username is None or password is None:
            return None
        
        # Try to find Customer by username first
        try:
            user = Customer.objects.get(username=username)
        except Customer.DoesNotExist:
            # If not found by username, try email (case-insensitive)
            try:
                user = Customer.objects.get(email__iexact=username)
            except Customer.DoesNotExist:
                return None
        
        # Verify password and check if user can authenticate
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        
        return None
    
    def get_user(self, user_id):
        # Only return Customer users
        try:
            return Customer.objects.get(pk=user_id)
        except Customer.DoesNotExist:
            pass
        
        return None


class StaffModelBackend(ModelBackend):
    """
    Custom authentication backend for Staff users.
    Used specifically for staff login in the admin panel.
    """
    
    def authenticate(self, request, username=None, password=None, **kwargs):
        """
        Authenticate a Staff user by username or email.
        """
        if username is None:
            username = kwargs.get('username')
        
        if username is None or password is None:
            return None
        
        # Try to find Staff by username first
        try:
            user = Staff.objects.get(username=username)
        except Staff.DoesNotExist:
            # If not found by username, try email (case-insensitive)
            try:
                user = Staff.objects.get(email__iexact=username)
            except Staff.DoesNotExist:
                return None
        
        # Verify password and check if user can authenticate
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        
        return None
    
    def get_user(self, user_id):
        """
        Retrieve a Staff user by ID.
        This is critical for session management.
        """
        try:
            return Staff.objects.get(pk=user_id)
        except Staff.DoesNotExist:
            pass
        
        return None


class SuperuserModelBackend(ModelBackend):
    """
    Custom authentication backend for Superuser users.
    Used specifically for superuser login in the admin panel.
    """
    
    def authenticate(self, request, username=None, password=None, **kwargs):
        """
        Authenticate a Superuser by username or email.
        """
        if username is None:
            username = kwargs.get('username')
        
        if username is None or password is None:
            return None
        
        # Try to find Superuser by username first
        try:
            user = Superuser.objects.get(username=username)
        except Superuser.DoesNotExist:
            # If not found by username, try email (case-insensitive)
            try:
                user = Superuser.objects.get(email__iexact=username)
            except Superuser.DoesNotExist:
                return None
        
        # Verify password and check if user can authenticate
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        
        return None
    
    def get_user(self, user_id):
        """
        Retrieve a Superuser by ID.
        This is critical for session management.
        """
        try:
            return Superuser.objects.get(pk=user_id)
        except Superuser.DoesNotExist:
            pass
        
        return None
