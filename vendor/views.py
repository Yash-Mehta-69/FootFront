from django.shortcuts import redirect, render, get_object_or_404
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from store.models import Category
from cart.models import Shipment, OrderItem
from django.utils import timezone
from datetime import timedelta, datetime

class MockObj:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


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
            # Mock Data
            products = [
                MockObj(pk=1, name="Nike Air Max", category="Sneakers", price=120.00, stock=50, image=MockObj(url="/static/images/hero-shoe.png"), status="Active", gender="M", is_trending=True),
                MockObj(pk=2, name="Adidas UltraBoost", category="Running", price=180.00, stock=30, image=MockObj(url="/static/images/hero-shoe.png"), status="Active", gender="U", is_trending=False),
                MockObj(pk=3, name="Puma Suede", category="Casual", price=90.00, stock=100, image=MockObj(url="/static/images/hero-shoe.png"), status="Inactive", gender="W", is_trending=False),
            ]
            return render(request, 'vendor_products.html', {'products': products})
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
            return redirect('vendor_shipments') # Orders are now managed via Shipments
        else:
            messages.info(request, f'Unaccessible page. Your role is {request.user.role}')
            return redirect('home')
    except Exception as e:
        print(f"Error in vendor_orders: {e}")
        return redirect('vendor_login')

def add_product(request):
    try:
        role = request.user.role
        if role == 'vendor':
            context = {
                'action': 'Add',
                'categories': [MockObj(pk=1, name="Sneakers"), MockObj(pk=2, name="Running"), MockObj(pk=3, name="Casual")],
                'sizes': [MockObj(pk=1, size_label="US 7"), MockObj(pk=2, size_label="US 8"), MockObj(pk=3, size_label="US 9"), MockObj(pk=4, size_label="US 10")],
                'colors': [MockObj(pk=1, name="Red", hex_code="#FF0000"), MockObj(pk=2, name="Blue", hex_code="#0000FF"), MockObj(pk=3, name="Black", hex_code="#000000")],
            }
            if request.method == "POST":
                messages.success(request, "Product added successfully (Mock)")
                return redirect('vendor_products')
            return render(request, 'vendor_add_product.html', context)
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
            product = MockObj(
                pk=1, 
                name="Nike Air Max", 
                category="Sneakers", 
                description="Classic air cushioning.",
                status="Active", 
                gender="M", 
                is_trending=True,
                variants=[
                    MockObj(size="US 8", color="Red", price="120.00", stock=15),
                    MockObj(size="US 9", color="Black", price="120.00", stock=35),
                ]
            )
            context = {
                'action': 'Edit',
                'product': product,
                'categories': [MockObj(pk=1, name="Sneakers"), MockObj(pk=2, name="Running"), MockObj(pk=3, name="Casual")],
                'sizes': [MockObj(pk=1, size_label="US 7"), MockObj(pk=2, size_label="US 8"), MockObj(pk=3, size_label="US 9"), MockObj(pk=4, size_label="US 10")],
                'colors': [MockObj(pk=1, name="Red", hex_code="#FF0000"), MockObj(pk=2, name="Blue", hex_code="#0000FF"), MockObj(pk=3, name="Black", hex_code="#000000")],
            }
            if request.method == "POST":
                messages.success(request, "Product updated successfully (Mock)")
                return redirect('vendor_products')
            return render(request, 'vendor_edit_product.html', context)
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

def vendor_categories(request):
    try:
        role = request.user.role
        if role == 'vendor':
            # Mock Data
            categories = [
                MockObj(name="Sneakers", description="All kinds of sneakers", image=MockObj(url="/static/images/hero-shoe.png")),
                MockObj(name="Running", description="Performance running shoes", image=MockObj(url="/static/images/hero-shoe.png")),
                MockObj(name="Casual", description="Everyday casual wear", image=MockObj(url="/static/images/hero-shoe.png")),
            ]
            return render(request, 'vendor_categories.html', {'categories': categories})
        else:
            messages.info(request, f'Unaccessible page. Your role is {request.user.role}')
            return redirect('home')
    except Exception as e:
        print(f"Error in vendor_categories: {e}")
        return redirect('vendor_login')

def vendor_shipments(request):
    try:
        role = request.user.role
        if role == 'vendor':
            # Mock Data
            shipments = [
                MockObj(
                    pk=101,
                    order_item=MockObj(
                        product_variant=MockObj(
                            product=MockObj(name="Nike Air Max"), 
                            size=MockObj(size_label="US 9"), 
                            color=MockObj(name="Red")
                        ),
                        order=MockObj(pk=1001)
                    ),
                    tracking_number="TRK9988776655",
                    courier_name="UPS",
                    status="pending",
                    shipped_at=datetime.now(),
                    expected_delivery=datetime.now() + timedelta(days=5)
                ),
                MockObj(
                    pk=102,
                    order_item=MockObj(
                        product_variant=MockObj(
                            product=MockObj(name="Adidas UltraBoost"), 
                            size=MockObj(size_label="US 10"), 
                            color=MockObj(name="Black")
                        ),
                        order=MockObj(pk=1002)
                    ),
                    tracking_number="TRK1122334455",
                    courier_name="DHL",
                    status="delivered",
                    shipped_at=datetime.now() - timedelta(days=3),
                    expected_delivery=datetime.now() - timedelta(days=1)
                )
            ]
            return render(request, 'vendor_shipments.html', {'shipments': shipments})
        else:
            messages.info(request, f'Unaccessible page. Your role is {request.user.role}')
            return redirect('home')
    except Exception as e:
        print(f"Error in vendor_shipments: {e}")
        return redirect('vendor_login')

def update_shipment_status(request, pk):
    try:
        if request.user.role != 'vendor':
             messages.error(request, 'Unauthorized access.')
             return redirect('home')

        return redirect(request.META.get('HTTP_REFERER', 'vendor_shipments'))

    except Exception as e:
        print(f"Error in update_shipment_status: {e}")
        messages.error(request, 'An error occurred.')
        return redirect(request.META.get('HTTP_REFERER', 'vendor_shipments'))

def create_shipment(request, order_item_id):
    try:
        if request.user.role != 'vendor':
             messages.error(request, 'Unauthorized access.')
             return redirect('home')

        if request.method == 'POST':
            messages.success(request, 'Shipment created successfully!')
        return redirect(request.META.get('HTTP_REFERER', 'vendor_orders'))

    except Exception as e:
        print(f"Error in create_shipment: {e}")
        messages.error(request, 'An error occurred.')
        return redirect('vendor_orders')

def vendor_profile(request):
    try:
        role = request.user.role
        if role == 'vendor':
            # Mock Data
            vendor = MockObj(
                shopName="Kicks Palace (Mock)",
                business_phone="1234567890",
                shopAddress="123 Dummy St, Mock City",
                description="This is a mock description for UI testing.",
                profile_picture=MockObj(url="/static/images/hero-shoe.png"), # Using existing image as placeholder
                panCard=None,
                adharCard=None,
                bank_detail=MockObj(
                    account_number="123456789012",
                    ifsc_code="HDFC0001234",
                    bank_name="HDFC Bank",
                    beneficiary_name="Kicks Palace Inc."
                )
            )
            
            if request.method == 'POST':
                messages.success(request, 'Profile updated successfully (Mock)!')
                return redirect('vendor_profile')

            return render(request, 'vendor_profile.html', {'vendor': vendor})
        else:
            messages.info(request, f'Unaccessible page. Your role is {request.user.role}')
            return redirect('home')
    except Exception as e:
        print(f"Error in vendor_profile: {e}")
        return redirect('vendor_login')

def vendor_analytics(request):
    try:
        role = request.user.role
        if role == 'vendor':
            # Mock Data
            analytics = MockObj(
                total_sales="$25,430",
                sales_growth="12.5",
                total_orders="1,245",
                orders_growth="5.8",
                avg_order_value="$125",
                aov_growth="1.2",
                products_sold="850",
                products_sold_growth="10.4"
            )
            return render(request, 'vendor_analytics.html', {'analytics': analytics})
        else:
            messages.info(request, f'Unaccessible page. Your role is {request.user.role}')
            return redirect('home')
    except Exception as e:
        print(f"Error in vendor_analytics: {e}")
        return redirect('vendor_login')

def vendor_help(request):
    try:
        role = request.user.role
        if role == 'vendor':
            return render(request, 'vendor_help.html')
        else:
            messages.info(request, f'Unaccessible page. Your role is {request.user.role}')
            return redirect('home')
    except Exception as e:
        print(f"Error in vendor_help: {e}")
        return redirect('vendor_login')

def vendor_reviews(request):
    try:
        role = request.user.role
        if role == 'vendor':
            # Mock Data
            reviews = [
                MockObj(pk=1, product="Nike Air Max", user="John Doe", rating=5, comment="Great quality!", date="2023-10-21"),
                MockObj(pk=2, product="Adidas UltraBoost", user="Jane Smith", rating=4, comment="Good, but shipping was slow.", date="2023-10-20"),
            ]
            return render(request, 'vendor_reviews.html', {'reviews': reviews})
        else:
            messages.info(request, f'Unaccessible page. Your role is {request.user.role}')
            return redirect('home')
    except Exception as e:
        print(f"Error in vendor_reviews: {e}")
        return redirect('vendor_login')

def vendor_change_password(request):
    try:
        role = request.user.role
        if role == 'vendor':
            if request.method == "POST":
                current_password = request.POST.get('current_password')
                new_password = request.POST.get('new_password')
                confirm_password = request.POST.get('confirm_password')

                if not request.user.check_password(current_password):
                    messages.error(request, "Incorrect current password.")
                elif new_password != confirm_password:
                    messages.error(request, "New passwords do not match.")
                else:
                    request.user.set_password(new_password)
                    request.user.save()
                    update_session_auth_hash(request, request.user)
                    messages.success(request, "Password changed successfully.")
                    return redirect('vendor_profile')
            
            return render(request, 'vendor_change_password.html')
        else:
            messages.info(request, f'Unaccessible page. Your role is {request.user.role}')
            return redirect('home')
    except Exception as e:
        print(f"Error in vendor_change_password: {e}")
        return redirect('vendor_login')
