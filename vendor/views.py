from django.shortcuts import redirect, render
from django.contrib import messages

# Create your views here.
def vendor_dashboard(request):
    print(f"User {request.user} accessing VENDOR dashboard")
    try:
        role = request.user.role
        if role == 'vendor':
            return render(request,'vendor_dashboard.html')
        else:
            messages.info(request,f'Unaccessible page. Your role is {request.user.role}')
            return redirect('home')
    except Exception as e:
        print(e)
        return redirect('vendor_login')

def vendor_products(request):
    try:
        role = request.user.role
        if role == 'vendor':
            return render(request, 'vendor_products.html')
        else:
            messages.info(request, f'Unaccessible page. Your role is {request.user.role}')
            return redirect('home')
    except Exception as e:
        print(e)
        return redirect('vendor_login')

def vendor_orders(request):
    try:
        role = request.user.role
        if role == 'vendor':
            return render(request, 'vendor_orders.html')
        else:
            messages.info(request, f'Unaccessible page. Your role is {request.user.role}')
            return redirect('home')
    except Exception as e:
        print(e)
        return redirect('vendor_login')

def add_product(request):
    try:
        role = request.user.role
        if role == 'vendor':
            return render(request, 'vendor_add_product.html')
        else:
            messages.info(request, f'Unaccessible page. Your role is {request.user.role}')
            return redirect('home')
    except Exception as e:
        print(e)
        return redirect('vendor_login')

def edit_product(request):
    try:
        role = request.user.role
        if role == 'vendor':
            return render(request, 'vendor_edit_product.html')
        else:
            messages.info(request, f'Unaccessible page. Your role is {request.user.role}')
            return redirect('home')
    except Exception as e:
        print(e)
        return redirect('vendor_login')

def product_detail(request):
    try:
        role = request.user.role
        if role == 'vendor':
            return render(request, 'vendor_product_detail.html')
        else:
            messages.info(request, f'Unaccessible page. Your role is {request.user.role}')
            return redirect('home')
    except Exception as e:
        print(e)
        return redirect('vendor_login')
