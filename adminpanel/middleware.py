"""
Middleware to redirect staff users from Django admin to custom adminpanel.
"""
from django.http import HttpResponseRedirect
from django.urls import reverse


class StaffAdminRedirectMiddleware:
    """
    Middleware that redirects staff users (non-superusers) from Django admin
    to the custom adminpanel dashboard.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Check if user is accessing Django admin (but not login/logout pages)
        if request.path.startswith('/admin/') and request.path not in ['/admin/login/', '/admin/logout/']:
            # If user is authenticated and is staff (but not superuser)
            if request.user.is_authenticated and request.user.is_staff and not request.user.is_superuser:
                # Redirect to adminpanel dashboard
                return HttpResponseRedirect(reverse('adminpanel:dashboard'))
        
        response = self.get_response(request)
        
        # After response, check if it's a redirect from admin login to admin index
        if (hasattr(response, 'status_code') and response.status_code == 302 and 
            hasattr(response, 'url') and '/admin/' in response.url and
            request.user.is_authenticated and 
            request.user.is_staff and not request.user.is_superuser):
            # Override redirect to go to adminpanel instead
            return HttpResponseRedirect(reverse('adminpanel:dashboard'))
        
        return response

