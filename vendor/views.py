from django.shortcuts import redirect, render, get_object_or_404
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from store.decorators import vendor_required
from store.models import Category
from cart.models import Shipment, OrderItem
from django.utils import timezone
from datetime import timedelta, datetime

class MockObj:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


# Create your views here.
@vendor_required
def vendor_dashboard(request):
    print(f"User {request.user} accessing VENDOR dashboard")
    return render(request,'vendor_dashboard.html')

@vendor_required
def vendor_products(request):
    # Mock Data
    products = [
        MockObj(pk=1, name="Nike Air Max", category="Sneakers", price=120.00, stock=50, image=MockObj(url="/static/images/hero-shoe.png"), status="Active", gender="M", is_trending=True),
        MockObj(pk=2, name="Adidas UltraBoost", category="Running", price=180.00, stock=30, image=MockObj(url="/static/images/hero-shoe.png"), status="Active", gender="U", is_trending=False),
        MockObj(pk=3, name="Puma Suede", category="Casual", price=90.00, stock=100, image=MockObj(url="/static/images/hero-shoe.png"), status="Inactive", gender="W", is_trending=False),
    ]
    return render(request, 'vendor_products.html', {'products': products})

@vendor_required
def vendor_orders(request):
    return redirect('vendor_shipments') # Orders are now managed via Shipments

@vendor_required
def add_product(request):
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

@vendor_required
def edit_product(request):
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

@vendor_required
def product_detail(request):
    return render(request, 'vendor_product_detail.html')

@vendor_required
def vendor_categories(request):
    # Mock Data
    categories = [
        MockObj(name="Sneakers", description="All kinds of sneakers", image=MockObj(url="/static/images/hero-shoe.png")),
        MockObj(name="Running", description="Performance running shoes", image=MockObj(url="/static/images/hero-shoe.png")),
        MockObj(name="Casual", description="Everyday casual wear", image=MockObj(url="/static/images/hero-shoe.png")),
    ]
    return render(request, 'vendor_categories.html', {'categories': categories})

@vendor_required
def vendor_shipments(request):
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

@vendor_required
def update_shipment_status(request, pk):
    return redirect(request.META.get('HTTP_REFERER', 'vendor_shipments'))

@vendor_required
def create_shipment(request, order_item_id):
    if request.method == 'POST':
        messages.success(request, 'Shipment created successfully!')
    return redirect(request.META.get('HTTP_REFERER', 'vendor_orders'))

@vendor_required
def vendor_profile(request):
    # Real Data
    vendor = request.user.vendor_profile
    
    # Prefetch bank details to avoid N+1 if accessed
    try:
        # Accessing the reverse relationship to ensure it's loaded or check existence
        _ = vendor.bankdetail 
    except Exception:
        pass # Handle cases where bank details might not exist yet

    if request.method == 'POST':
        # Handle simple profile updates here if needed, or redirect to an edit page
        messages.info(request, 'Profile update feature coming soon.')
        return redirect('vendor_profile')

    return render(request, 'vendor_profile.html', {'vendor': vendor})

@vendor_required
def vendor_analytics(request):
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

@vendor_required
def vendor_help(request):
    return render(request, 'vendor_help.html')

@vendor_required
def vendor_reviews(request):
    # Mock Data
    reviews = [
        MockObj(pk=1, product="Nike Air Max", user="John Doe", rating=5, comment="Great quality!", date="2023-10-21"),
        MockObj(pk=2, product="Adidas UltraBoost", user="Jane Smith", rating=4, comment="Good, but shipping was slow.", date="2023-10-20"),
    ]
    return render(request, 'vendor_reviews.html', {'reviews': reviews})

@vendor_required
def vendor_change_password(request):
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
