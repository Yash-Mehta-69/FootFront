from django.shortcuts import redirect, render, get_object_or_404
from django.contrib import messages
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
                MockObj(name="Nike Air Max", price=120, stock=50, category=MockObj(name="Sneakers"), image=MockObj(url="/static/images/hero-shoe.png"), is_active=True),
                MockObj(name="Adidas UltraBoost", price=180, stock=30, category=MockObj(name="Running"), image=MockObj(url="/static/images/hero-shoe.png"), is_active=True),
                MockObj(name="Puma Suede", price=90, stock=100, category=MockObj(name="Casual"), image=MockObj(url="/static/images/hero-shoe.png"), is_active=False),
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
            # Mock Data
            order_items = [
                MockObj(
                    pk=1,
                    price=150,
                    quantity=1,
                    order=MockObj(
                        pk=1001,
                        order_date=datetime.now(),
                        customer=MockObj(
                            user=MockObj(first_name="Alice", last_name="Smith", email="alice@example.com"),
                            phone="1234567890"
                        ),
                        shipping_address=MockObj(
                            address_line1="123 Maple St", city="New York", state="NY", postal_code="10001"
                        ),
                        payment=MockObj(status="success")
                    ),
                    product_variant=MockObj(
                        product=MockObj(name="Nike Air Max"),
                        size=MockObj(size_label="US 9"),
                        color=MockObj(name="Red"),
                        image=MockObj(url="/static/images/hero-shoe.png")
                    ),
                    shipment=None
                ),
                MockObj(
                    pk=2,
                    price=220,
                    quantity=2,
                    order=MockObj(
                        pk=1002,
                        order_date=datetime.now() - timedelta(days=1),
                        customer=MockObj(
                            user=MockObj(first_name="Bob", last_name="Jones", email="bob@example.com"),
                            phone="9876543210"
                        ),
                        shipping_address=MockObj(
                            address_line1="456 Oak Ave", city="Los Angeles", state="CA", postal_code="90001"
                        ),
                        payment=MockObj(status="success")
                    ),
                    product_variant=MockObj(
                        product=MockObj(name="Adidas UltraBoost"),
                        size=MockObj(size_label="US 10"),
                        color=MockObj(name="Black"),
                        image=MockObj(url="/static/images/hero-shoe.png")
                    ),
                    shipment=MockObj(
                        pk=501,
                        tracking_number="TRK123456789",
                        courier_name="FedEx",
                        status="shipped"
                    )
                )
            ]
            return render(request, 'vendor_orders.html', {'order_items': order_items})
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
                    order_item=MockObj(product_variant=MockObj(product=MockObj(name="Nike Air Max"), size=MockObj(size_label="US 9"), color=MockObj(name="Red"))),
                    tracking_number="TRK9988776655",
                    courier_name="UPS",
                    status="pending",
                    shipped_at=datetime.now(),
                    expected_delivery=datetime.now() + timedelta(days=5)
                ),
                MockObj(
                    pk=102,
                    order_item=MockObj(product_variant=MockObj(product=MockObj(name="Adidas UltraBoost"), size=MockObj(size_label="US 10"), color=MockObj(name="Black"))),
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
