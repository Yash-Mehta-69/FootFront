from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth import logout
from .models import Customer

class BlockedUserMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            try:
                # Assuming the user has a linked customer profile
                if hasattr(request.user, 'customer_profile'):
                    customer = request.user.customer_profile
                    if customer.is_blocked:
                         logout(request)
                         messages.error(request, 'Your account has been suspended. Please contact support.')
                         return redirect('login')
                    
                    if customer.is_deleted:
                        logout(request)
                        messages.error(request, 'Account not found.')
                        return redirect('login')

            except Customer.DoesNotExist:
                pass

            # Vendor Blocking Check
            if hasattr(request.user, 'vendor_profile'):
                vendor = request.user.vendor_profile
                if vendor.is_blocked:
                        logout(request)
                        messages.error(request, 'Your vendor account has been suspended.')
                        return redirect('vendor_login')
                if vendor.is_deleted:
                        logout(request)
                        messages.error(request, 'Vendor account not found.')
                        return redirect('vendor_login')

        response = self.get_response(request)
        return response
