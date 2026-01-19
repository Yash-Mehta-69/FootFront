from django.shortcuts import redirect
from functools import wraps
from django.contrib.auth.decorators import user_passes_test, login_required
from django.shortcuts import redirect
from django.contrib import messages

def redirect_special_users(view_func):
    """
    Redirects Admins and Vendors to their respective dashboards if they try to access customer pages.
    """
    @wraps(view_func)
    def wrapper_func(request, *args, **kwargs):
        if request.user.is_authenticated:
            if request.user.role == 'vendor':
                return redirect('vendordashboard')
            elif request.user.role == 'admin':
                return redirect('admin_dashboard')
        return view_func(request, *args, **kwargs)
    return wrapper_func



def admin_required(view_func):
    """
    Decorator for views that checks that the user is logged in and is an admin.
    Redirects to admin login if not authorized.
    """
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('admin_login')
        
        if request.user.role == 'admin' or request.user.is_superuser:
            return view_func(request, *args, **kwargs)
            
        messages.error(request, "Access Denied: Admin privileges required.")
        return redirect('admin_login')
        
    return _wrapped_view

def vendor_required(view_func):
    """
    Decorator for views that checks that the user is logged in and is a vendor.
    Redirects to vendor login if not authorized.
    """
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('vendor_login')
        
        if request.user.role == 'vendor':
            return view_func(request, *args, **kwargs)
            
        messages.error(request, "Access Denied: Vendor privileges required.")
        return redirect('vendor_login')
        
    return _wrapped_view