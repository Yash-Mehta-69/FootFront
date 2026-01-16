from django.shortcuts import render, redirect
from django.contrib import messages
from datetime import datetime, timedelta

class MockObj:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

# Create your views here.
def dashboard(request):
    # Mock Stats
    stats = {
        'total_users': 1250,
        'users_growth': 5.4,
        'total_products': 450,
        'products_growth': 2.1,
        'total_orders': 328,
        'orders_growth': 12.5,
        'total_revenue': "$45,230",
        'revenue_growth': 8.2
    }
    
    # Mock Recent Orders
    recent_orders = [
        MockObj(pk="#ORD-001", customer_name="John Doe", product="Nike Air Max", date="Oct 15, 2023", status="Completed", amount="$120.00", status_class="success"),
        MockObj(pk="#ORD-002", customer_name="Jane Smith", product="Adidas Ultraboost", date="Oct 14, 2023", status="Pending", amount="$180.00", status_class="warning"),
        MockObj(pk="#ORD-003", customer_name="Mike Ross", product="Puma Suede", date="Oct 12, 2023", status="Cancelled", amount="$85.00", status_class="danger"),
    ]
    
    context = {
        'stats': stats,
        'recent_orders': recent_orders
    }
    return render(request, 'dashboard/admin_dashboard.html', context)

def manage_users(request):
    users = [
        MockObj(pk=1, name="John Doe", email="john@example.com", role="Customer", status="Active", join_date="Jan 10, 2023"),
        MockObj(pk=2, name="Jane Smith", email="jane@example.com", role="Vendor", status="Active", join_date="Feb 15, 2023"),
        MockObj(pk=3, name="Mike Ross", email="mike@example.com", role="Customer", status="Inactive", join_date="Mar 05, 2023"),
    ]
    return render(request, 'dashboard/manage_users.html', {'users': users})

def add_user(request):
    if request.method == "POST":
        messages.success(request, "User added successfully (Mock)")
        return redirect('manage_users')
    return render(request, 'dashboard/user_form.html', {'action': 'Add'})

def edit_user(request, pk):
    if request.method == "POST":
        messages.success(request, "User updated successfully (Mock)")
        return redirect('manage_users')
    user = MockObj(pk=pk, name="John Doe", email="john@example.com", role="Customer", status="Active")
    return render(request, 'dashboard/user_form.html', {'action': 'Edit', 'user': user})

def manage_categories(request):
    categories = [
        MockObj(pk=1, name="Sneakers", description="All kinds of sneakers", product_count=120, status="Active"),
        MockObj(pk=2, name="Running", description="Performance running shoes", product_count=85, status="Active"),
        MockObj(pk=3, name="Casual", description="Everyday casual wear", product_count=200, status="Inactive"),
    ]
    return render(request, 'dashboard/manage_categories.html', {'categories': categories})

def add_category(request):
    if request.method == "POST":
        messages.success(request, "Category added successfully (Mock)")
        return redirect('manage_categories')
    return render(request, 'dashboard/category_form.html', {'action': 'Add'})

def edit_category(request, pk):
    if request.method == "POST":
        messages.success(request, "Category updated successfully (Mock)")
        return redirect('manage_categories')
    category = MockObj(pk=pk, name="Sneakers", description="All kinds of sneakers", status="Active")
    return render(request, 'dashboard/category_form.html', {'action': 'Edit', 'category': category})

def manage_products(request):
    products = [
        MockObj(pk=1, name="Nike Air Max", category="Sneakers", price="$120", stock=50, vendor="Kicks Palace", status="Active", image="/static/images/hero-shoe.png"),
        MockObj(pk=2, name="Adidas UltraBoost", category="Running", price="$180", stock=30, vendor="Run World", status="Active", image="/static/images/hero-shoe.png"),
        MockObj(pk=3, name="Puma Suede", category="Casual", price="$90", stock=0, vendor="Style Hub", status="Out of Stock", image="/static/images/hero-shoe.png"),
    ]
    return render(request, 'dashboard/manage_products.html', {'products': products})

def add_product(request):
    if request.method == "POST":
        messages.success(request, "Product added successfully (Mock)")
        return redirect('manage_products')
    return render(request, 'dashboard/product_form.html', {'action': 'Add'})

def edit_product(request, pk):
    if request.method == "POST":
        messages.success(request, "Product updated successfully (Mock)")
        return redirect('manage_products')
    product = MockObj(pk=pk, name="Nike Air Max", category="Sneakers", price=120, stock=50, description="Great shoe", status="Active")
    return render(request, 'dashboard/product_form.html', {'action': 'Edit', 'product': product})

def manage_orders(request):
    orders = [
        MockObj(pk=1001, customer="Alice Smith", date="2023-10-20", total="$150", status="Processing", payment_status="Paid"),
        MockObj(pk=1002, customer="Bob Jones", date="2023-10-19", total="$220", status="Shipped", payment_status="Paid"),
        MockObj(pk=1003, customer="Charlie Brown", date="2023-10-18", total="$80", status="Cancelled", payment_status="Refunded"),
    ]
    return render(request, 'dashboard/manage_orders.html', {'orders': orders})

def order_detail(request, pk):
    order = MockObj(
        pk=pk,
        customer=MockObj(name="Alice Smith", email="alice@example.com", phone="1234567890"),
        shipping_address="123 Maple St, New York, NY 10001",
        date="2023-10-20",
        status="Processing",
        payment_status="Paid",
        subtotal="$140",
        shipping="$10",
        total="$150",
        items=[
            MockObj(product="Nike Air Max", quantity=1, price="$140", image="/static/images/hero-shoe.png")
        ]
    )
    return render(request, 'dashboard/order_detail.html', {'order': order})

def manage_payments(request):
    payments = [
        MockObj(pk="PAY-12345", user="Alice Smith", amount="$150", method="Credit Card", status="Success", date="2023-10-20"),
        MockObj(pk="PAY-67890", user="Bob Jones", amount="$220", method="PayPal", status="Success", date="2023-10-19"),
        MockObj(pk="PAY-11223", user="Charlie Brown", amount="$80", method="Credit Card", status="Refunded", date="2023-10-18"),
    ]
    return render(request, 'dashboard/manage_payments.html', {'payments': payments})

def view_reviews(request):
    reviews = [
        MockObj(pk=1, product="Nike Air Max", user="John Doe", rating=5, comment="Love these shoes!", date="2023-10-21"),
        MockObj(pk=2, product="Adidas UltraBoost", user="Jane Smith", rating=4, comment="Very comfortable but expensive.", date="2023-10-20"),
    ]
    return render(request, 'dashboard/view_reviews.html', {'reviews': reviews})

def view_complaints(request):
    complaints = [
        MockObj(pk=1, user="Mike Ross", subject="Late Delivery", message="My order is 3 days late.", date="2023-10-21", status="Open"),
        MockObj(pk=2, user="Rachel Green", subject="Wrong Item", message="I received the wrong size.", date="2023-10-19", status="Resolved"),
    ]
    return render(request, 'dashboard/view_complaints.html', {'complaints': complaints})

def admin_profile(request):
    if request.method == "POST":
        messages.success(request, "Profile updated successfully (Mock)")
    admin = MockObj(
        first_name="Admin",
        last_name="User",
        email="admin@footfront.com",
        phone="9876543210",
        profile_picture="/static/images/hero-shoe.png"
    )
    return render(request, 'dashboard/admin_profile.html', {'admin': admin})

def change_password(request):
    if request.method == "POST":
        messages.success(request, "Password changed successfully (Mock)")
        return redirect('admin_profile')
    return render(request, 'dashboard/change_password.html')