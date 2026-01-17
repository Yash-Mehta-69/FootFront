from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
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

def manage_customers(request):
    customers = [
        MockObj(pk=1, name="John Doe", email="john@example.com", phone="1234567890", role="Customer", status="Active", join_date="Jan 10, 2023", is_blocked=False, firebase_uid="uid_12345"),
        MockObj(pk=3, name="Mike Ross", email="mike@example.com", phone="9876543210", role="Customer", status="Inactive", join_date="Mar 05, 2023", is_blocked=True, firebase_uid="uid_67890"),
    ]
    return render(request, 'dashboard/manage_customers.html', {'customers': customers})

def add_customer(request):
    if request.method == "POST":
        messages.success(request, "Customer added successfully (Mock)")
        return redirect('manage_customers')
    return render(request, 'dashboard/user_form.html', {'action': 'Add', 'role': 'Customer', 'return_url': 'manage_customers'})

def edit_customer(request, pk):
    if request.method == "POST":
        messages.success(request, "Customer updated successfully (Mock)")
        return redirect('manage_customers')
    user = MockObj(pk=pk, name="John Doe", email="john@example.com", phone="1234567890", role="Customer", status="Active", is_blocked=False, firebase_uid="uid_12345")
    return render(request, 'dashboard/user_form.html', {'action': 'Edit', 'role': 'Customer', 'user': user, 'return_url': 'manage_customers'})

def manage_vendors(request):
    vendors = [
        MockObj(
            pk=2, 
            name="Jane Smith", 
            email="jane@example.com", 
            shopName="Kicks Palace", 
            shopAddress="123 Sneaker St, NY",
            business_phone="1122334455",
            description="Best sneakers in town",
            role="Vendor", 
            status="Active", 
            join_date="Feb 15, 2023", 
            is_blocked=False,
            profile_picture="path/to/img",
            panCard="path/to/img",
            adharCard="path/to/img",
            bank_detail=MockObj(bank_name="HDFC Bank", account_number="1234567890", ifsc_code="HDFC000123", beneficiary_name="Jane Smith")
        ),
        MockObj(
            pk=4, 
            name="Peter Parker", 
            email="peter@example.com", 
            shopName="Spidey Shoes", 
            shopAddress="20 Ingram St, Queens",
            business_phone="5566778899",
            description="Friendly neighborhood shoe seller",
            role="Vendor", 
            status="Active", 
            join_date="Oct 20, 2023", 
            is_blocked=False,
            profile_picture="path/to/img",
            panCard="path/to/img",
            adharCard="path/to/img",
            bank_detail=MockObj(bank_name="SBI", account_number="0987654321", ifsc_code="SBIN000456", beneficiary_name="Peter Parker")
        ),
    ]
    return render(request, 'dashboard/manage_vendors.html', {'vendors': vendors})

def add_vendor(request):
    if request.method == "POST":
        messages.success(request, "Vendor added successfully (Mock)")
        return redirect('manage_vendors')
    return render(request, 'dashboard/user_form.html', {'action': 'Add', 'role': 'Vendor', 'return_url': 'manage_vendors'})

def edit_vendor(request, pk):
    if request.method == "POST":
        messages.success(request, "Vendor updated successfully (Mock)")
        return redirect('manage_vendors')
    user = MockObj(
        pk=pk, 
        name="Jane Smith", 
        email="jane@example.com", 
        shopName="Kicks Palace", 
        shopAddress="123 Sneaker St, NY",
        business_phone="1122334455",
        description="Best sneakers in town",
        role="Vendor", 
        status="Active",
        is_blocked=False,
        profile_picture="path/to/img",
        panCard="path/to/img",
        adharCard="path/to/img",
        bank_detail=MockObj(bank_name="HDFC Bank", account_number="1234567890", ifsc_code="HDFC000123", beneficiary_name="Jane Smith")
    )
    return render(request, 'dashboard/user_form.html', {'action': 'Edit', 'role': 'Vendor', 'user': user, 'return_url': 'manage_vendors'})

def manage_categories(request):
    categories = [
        MockObj(pk=1, name="Sneakers", parent="Men", description="Casual daily wear shoes", status="Active", count=120),
        MockObj(pk=2, name="Running", parent="Sports", description="Performance running shoes", status="Active", count=85),
    ]
    return render(request, 'dashboard/manage_categories.html', {'categories': categories})

def add_category(request):
    parents = [MockObj(pk=10, name="Men"), MockObj(pk=11, name="Women"), MockObj(pk=12, name="Sports")]
    if request.method == "POST":
        messages.success(request, "Category added successfully (Mock)")
        return redirect('manage_categories')
    return render(request, 'dashboard/category_form.html', {'action': 'Add', 'parents': parents})

def edit_category(request, pk):
    parents = [MockObj(pk=10, name="Men"), MockObj(pk=11, name="Women"), MockObj(pk=12, name="Sports")]
    if request.method == "POST":
        messages.success(request, "Category updated successfully (Mock)")
        return redirect('manage_categories')
    category = MockObj(pk=pk, name="Sneakers", parent="Men", description="Casual daily wear shoes", status="Active")
    return render(request, 'dashboard/category_form.html', {'action': 'Edit', 'category': category, 'parents': parents})

def manage_products(request):
    products = [
        MockObj(pk=1, name="Nike Air Max", category="Sneakers", vendor="Kicks Palace", price="120.00", stock=50, status="Active", image="path/to/img", gender="M", is_trending=True),
        MockObj(pk=2, name="Adidas Ultraboost", category="Running", vendor="Spidey Shoes", price="180.00", stock=30, status="Active", image="path/to/img", gender="U", is_trending=False),
        MockObj(pk=3, name="Puma Suede", category="Sneakers", vendor="Kicks Palace", price="85.00", stock=0, status="Inactive", image="path/to/img", gender="W", is_trending=False),
    ]
    return render(request, 'dashboard/manage_products.html', {'products': products})

def add_product(request):
    context = {
        'action': 'Add',
        'vendors': [MockObj(pk=1, shopName="Kicks Palace"), MockObj(pk=2, shopName="Spidey Shoes")],
        'categories': [MockObj(pk=1, name="Sneakers"), MockObj(pk=2, name="Running"), MockObj(pk=3, name="Casual")],
        'sizes': [MockObj(pk=1, size_label="US 7"), MockObj(pk=2, size_label="US 8"), MockObj(pk=3, size_label="US 9"), MockObj(pk=4, size_label="US 10")],
        'colors': [MockObj(pk=1, name="Red", hex_code="#FF0000"), MockObj(pk=2, name="Blue", hex_code="#0000FF"), MockObj(pk=3, name="Black", hex_code="#000000")],
    }
    if request.method == "POST":
        messages.success(request, "Product added successfully (Mock)")
        return redirect('manage_products')
    return render(request, 'dashboard/product_form.html', context)

def edit_product(request, pk):
    product = MockObj(
        pk=pk, 
        name="Nike Air Max", 
        category="Sneakers", 
        vendor="Kicks Palace", 
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
        'vendors': [MockObj(pk=1, shopName="Kicks Palace"), MockObj(pk=2, shopName="Spidey Shoes")],
        'categories': [MockObj(pk=1, name="Sneakers"), MockObj(pk=2, name="Running"), MockObj(pk=3, name="Casual")],
        'sizes': [MockObj(pk=1, size_label="US 7"), MockObj(pk=2, size_label="US 8"), MockObj(pk=3, size_label="US 9"), MockObj(pk=4, size_label="US 10")],
        'colors': [MockObj(pk=1, name="Red", hex_code="#FF0000"), MockObj(pk=2, name="Blue", hex_code="#0000FF"), MockObj(pk=3, name="Black", hex_code="#000000")],
    }
    if request.method == "POST":
        messages.success(request, "Product updated successfully (Mock)")
        return redirect('manage_products')
    return render(request, 'dashboard/product_form.html', context)

def manage_orders(request):
    orders = [
        MockObj(pk=1001, customer="Alice Smith", date="2023-10-20", total="$150", status="Processing", payment_status="Paid"),
        MockObj(pk=1002, customer="Bob Jones", date="2023-10-19", total="$220", status="Shipped", payment_status="Paid"),
        MockObj(pk=1003, customer="Charlie Brown", date="2023-10-18", total="$80", status="Cancelled", payment_status="Refunded"),
    ]
    vendors = [MockObj(pk=1, shopName="Kicks Palace"), MockObj(pk=2, shopName="Sporty Shoes")]
    return render(request, 'dashboard/manage_orders.html', {'orders': orders, 'vendors': vendors})

def admin_edit_order(request, pk):
    # Mock order fetching
    order = MockObj(
        pk=pk, 
        customer="Alice Smith", 
        date="2023-10-20", 
        total="$150", 
        status="Processing", 
        payment_status="Paid"
    )
    
    if request.method == "POST":
        new_status = request.POST.get('status')
        new_payment = request.POST.get('payment_status')
        messages.success(request, f"Order #{pk} updated successfully (Status: {new_status}, Payment: {new_payment}) - Mock")
        return redirect('manage_orders')
        
    return render(request, 'dashboard/edit_order.html', {'order': order})

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

def manage_shipments(request):
    # Mock Data
    shipments = [
        MockObj(
            pk=501,
            order_item=MockObj(
                order=MockObj(pk=1001),
                product_variant=MockObj(product=MockObj(name="Nike Air Max"), size=MockObj(size_label="US 9"), color=MockObj(name="Red"))
            ),
            tracking_number="TRK9988776655",
            vendor=MockObj(shopName="Kicks Palace"),
            courier_name="UPS",
            status="pending",
            shipped_at=datetime.now(),
            expected_delivery=datetime.now() + timedelta(days=5)
        ),
        MockObj(
            pk=502,
            order_item=MockObj(
                order=MockObj(pk=1002),
                product_variant=MockObj(product=MockObj(name="Adidas UltraBoost"), size=MockObj(size_label="US 10"), color=MockObj(name="Black"))
            ),
            tracking_number="TRK1122334455",
            vendor=MockObj(shopName="Sporty Shoes"),
            courier_name="DHL",
            status="delivered",
            shipped_at=datetime.now() - timedelta(days=3),
            expected_delivery=datetime.now() - timedelta(days=1)
        )
    ]
    vendors = [MockObj(pk=1, shopName="Kicks Palace"), MockObj(pk=2, shopName="Sporty Shoes")]
    return render(request, 'dashboard/manage_shipments.html', {'shipments': shipments, 'vendors': vendors})

def admin_update_shipment_status(request, pk):
    try:
        if request.user.role != 'admin':
             # Note: In real app, check permissions properly
             pass

        if request.method == "POST":
            new_status = request.POST.get('status')
            messages.success(request, f"Shipment #{pk} status updated to '{new_status}' successfully (Mock)")
            return redirect('manage_shipments')

        return redirect('manage_shipments')

    except Exception as e:
        print(f"Error in admin_update_shipment_status: {e}")
        messages.error(request, 'An error occurred.')
        return redirect('manage_shipments')

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

def delete_review(request, pk):
    try:
        # Mock deletion logic
        if request.method == "POST":
            messages.success(request, f"Review #{pk} deleted successfully (Mock)")
            return redirect('view_reviews')
        return redirect('view_reviews')
    except Exception as e:
        print(f"Error in delete_review: {e}")
        messages.error(request, 'An error occurred.')
        return redirect('view_reviews')

def view_complaints(request):
    complaints = [
        MockObj(pk=1, user="Mike Ross", subject="Late Delivery", message="My order is 3 days late.", date="2023-10-21", status="Open"),
        MockObj(pk=2, user="Rachel Green", subject="Wrong Item", message="I received the wrong size.", date="2023-10-19", status="Resolved"),
    ]
    return render(request, 'dashboard/view_complaints.html', {'complaints': complaints})

def delete_complaint(request, pk):
    try:
        # Mock deletion logic
        if request.method == "POST":
            messages.success(request, f"Complaint #{pk} deleted successfully (Mock)")
            return redirect('view_complaints')
        return redirect('view_complaints')
    except Exception as e:
        print(f"Error in delete_complaint: {e}")
        messages.error(request, 'An error occurred.')
        return redirect('view_complaints')

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
            update_session_auth_hash(request, request.user)  # Important!
            messages.success(request, "Password changed successfully.")
            return redirect('admin_profile')

    return render(request, 'dashboard/change_password.html')