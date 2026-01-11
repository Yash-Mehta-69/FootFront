from django.shortcuts import redirect
from functools import wraps

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
                return redirect('/admin/')
        return view_func(request, *args, **kwargs)
    return wrapper_func