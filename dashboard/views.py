from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from store.decorators import admin_required
from datetime import datetime, timedelta
import firebase_admin
from firebase_admin import auth
import re
from django.core.validators import validate_email
from django.core.exceptions import ValidationError

class MockObj:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

# Create your views here.
@admin_required
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

from store.models import Customer

@admin_required
def manage_customers(request):
    customers = Customer.objects.select_related('user').all()
    return render(request, 'dashboard/manage_customers.html', {'customers': customers})

@admin_required
def add_customer(request):
    form_data = {}
    errors = {}
    
    if request.method == "POST":
        form_data = request.POST.dict()
        
        # Validation
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        email = request.POST.get('email', '').strip()
        phone = request.POST.get('phone', '').strip()
        password = request.POST.get('password', '')
        confirm_password = request.POST.get('confirm_password', '')
        
        if not re.match(r'^[a-zA-Z\s]+$', first_name): errors['first_name'] = "First name must contain only letters."
        if not re.match(r'^[a-zA-Z\s]+$', last_name): errors['last_name'] = "Last name must contain only letters."
        
        try:
            validate_email(email)
        except ValidationError:
            errors['email'] = "Invalid email format."
            
        if User.objects.filter(email=email).exists():
            errors['email'] = "Email is already registered."
            
        if phone and (not phone.isdigit() or len(phone) != 10):
            errors['phone'] = "Phone number must be exactly 10 digits."
            
        if password != confirm_password:
            errors['confirm_password'] = "Passwords do not match."
            
        if not errors:
            try:
                user = User.objects.create_user(
                    email=email,
                    password=password,
                    first_name=first_name,
                    last_name=last_name,
                    role='customer'
                )
                Customer.objects.create(
                    user=user, 
                    phone=phone,
                    is_blocked=(request.POST.get('status', 'Active') != 'Active')
                )
                messages.success(request, "Customer added successfully.")
                return redirect('manage_customers')
            except Exception as e:
                messages.error(request, f"Error adding customer: {e}")
        
    return render(request, 'dashboard/user_form.html', {
        'action': 'Add', 
        'role': 'Customer', 
        'return_url': 'manage_customers',
        'form_data': form_data,
        'errors': errors
    })

@admin_required
def edit_customer(request, pk):
    try:
        customer = Customer.objects.select_related('user').get(pk=pk)
    except Customer.DoesNotExist:
        messages.error(request, "Customer not found.")
        return redirect('manage_customers')

    form_data = None
    errors = {}

    if request.method == "POST":
        form_data = request.POST.dict()
        
        # Validation
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        email = request.POST.get('email', '').strip()
        phone = request.POST.get('phone', '').strip()
        
        if not re.match(r'^[a-zA-Z\s]+$', first_name): errors['first_name'] = "First name must contain only letters."
        if not re.match(r'^[a-zA-Z\s]+$', last_name): errors['last_name'] = "Last name must contain only letters."
        
        try:
            validate_email(email)
        except ValidationError:
            errors['email'] = "Invalid email format."
            
        if User.objects.filter(email=email).exclude(pk=customer.user.pk).exists():
            errors['email'] = "Email is already in use by another user."

        if phone and (not phone.isdigit() or len(phone) != 10):
            errors['phone'] = "Phone number must be exactly 10 digits."

        if not errors:
            # Update User fields
            customer.user.first_name = first_name
            customer.user.last_name = last_name
            customer.user.email = email
            
            # Update Customer fields
            customer.phone = phone
            
            status = request.POST.get('status')
            if status == 'Active':
                customer.is_blocked = False
            else:
                customer.is_blocked = True
                
            try:
                customer.user.save()
                customer.save()
                messages.success(request, "Customer updated successfully.")
                return redirect('manage_customers')
            except Exception as e:
                messages.error(request, f"Error updating customer: {e}")
                
    else:
        # Initial Form Data
        form_data = {
            'first_name': customer.user.first_name,
            'last_name': customer.user.last_name,
            'email': customer.user.email,
            'phone': customer.phone,
            'status': 'Active' if not customer.is_blocked else 'Blocked'
        }

    return render(request, 'dashboard/user_form.html', {
        'action': 'Edit', 
        'role': 'Customer', 
        'customer_obj': customer, # For read-only fields like UID
        'form_data': form_data,
        'errors': errors,
        'return_url': 'manage_customers'
    })

@admin_required
def delete_customer(request, pk):
    try:
        customer = Customer.objects.get(pk=pk)
        
        # Delete from Firebase Auth
        if customer.firebase_uid:
            try:
                auth.delete_user(customer.firebase_uid)
                print(f"DEBUG: Deleted Firebase user {customer.firebase_uid}")
            except auth.UserNotFoundError:
                print(f"DEBUG: Firebase user {customer.firebase_uid} not found, already deleted.")
            except Exception as fb_err:
                print(f"DEBUG: Error deleting from Firebase: {fb_err}")
                # We continue with local soft delete even if firebase fails
        
        customer.is_deleted = True
        customer.firebase_uid = None # Clear UID so it can be reused or simply to detach
        customer.save()
        
        messages.success(request, "Customer deleted successfully (Firebase & Local).")
    except Customer.DoesNotExist:
        messages.error(request, "Customer not found.")
    except Exception as e:
        messages.error(request, f"Error deleting customer: {e}")
        
    return redirect('manage_customers')

from vendor.models import Vendor, BankDetail
from django.db import transaction
from store.models import User

@admin_required
def manage_vendors(request):
    vendors = Vendor.objects.select_related('user', 'bankdetail').filter(is_deleted=False)
    # Map mock attributes for template compatibility if needed, or update template
    # Template expects: vendor.pk, vendor.shopName, vendor.name (user.first_name + last), vendor.email, vendor.business_phone, vendor.status
    # We will pass the queryset directly and update the template to access relational fields
    return render(request, 'dashboard/manage_vendors.html', {'vendors': vendors})

@admin_required
def add_vendor(request):
    form_data = {}
    errors = {}
    
    if request.method == "POST":
        form_data = request.POST.dict()
        
        # Validation
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        confirm_password = request.POST.get('confirm_password', '')
        shop_name = request.POST.get('shopName', '').strip()
        business_phone = request.POST.get('business_phone', '').strip()
        
        if not re.match(r'^[a-zA-Z\s]+$', first_name): errors['first_name'] = "First name must contain only letters."
        if not re.match(r'^[a-zA-Z\s]+$', last_name): errors['last_name'] = "Last name must contain only letters."
        
        try:
            validate_email(email)
        except ValidationError:
            errors['email'] = "Invalid email format."
            
        if User.objects.filter(email=email).exists(): errors['email'] = "Email already registered."
        
        if password != confirm_password: errors['confirm_password'] = "Passwords do not match."
        
        if Vendor.objects.filter(shopName=shop_name).exists(): errors['shopName'] = "Shop name is already taken."
        
        if not business_phone.isdigit() or len(business_phone) != 10:
            errors['business_phone'] = "Phone number must be exactly 10 digits."
            
        if not errors:
            try:
                with transaction.atomic():
                    # 1. Create User
                    user = User.objects.create_user(
                        email=email,
                        password=password,
                        first_name=first_name,
                        last_name=last_name,
                        role='vendor'
                    )
                    
                    # 2. Create Vendor Profile
                    vendor = Vendor.objects.create(
                        user=user,
                        shopName=shop_name,
                        shopAddress=request.POST.get('shopAddress'),
                        business_phone=business_phone,
                        description=request.POST.get('description'),
                        is_blocked=(request.POST.get('status', 'Active') != 'Active')
                    )
                    
                    # Handle Files
                    if request.FILES.get('profile_picture'):
                        vendor.profile_picture = request.FILES['profile_picture']
                    if request.FILES.get('panCard'):
                        vendor.panCard = request.FILES['panCard']
                    if request.FILES.get('adharCard'):
                        vendor.adharCard = request.FILES['adharCard']
                    vendor.save()
    
                    # 3. Create Bank Details
                    BankDetail.objects.create(
                        vendor=vendor,
                        bank_name=request.POST.get('bank_name'),
                        account_number=request.POST.get('account_number'),
                        ifsc_code=request.POST.get('ifsc_code'),
                        beneficiary_name=request.POST.get('beneficiary_name')
                    )
                    
                    messages.success(request, "Vendor added successfully.")
                    return redirect('manage_vendors')
            except Exception as e:
                messages.error(request, f"Error adding vendor: {e}")

    return render(request, 'dashboard/user_form.html', {
        'action': 'Add', 
        'role': 'Vendor', 
        'return_url': 'manage_vendors',
        'form_data': form_data,
        'errors': errors
    })

@admin_required
def edit_vendor(request, pk):
    try:
        vendor = Vendor.objects.select_related('user', 'bankdetail').get(pk=pk)
    except Vendor.DoesNotExist:
        messages.error(request, "Vendor not found.")
        return redirect('manage_vendors')

    form_data = None
    errors = {}

    if request.method == "POST":
        form_data = request.POST.dict()
        
        # Validation
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        email = request.POST.get('email', '').strip()
        shop_name = request.POST.get('shopName', '').strip()
        business_phone = request.POST.get('business_phone', '').strip()
        
        if not re.match(r'^[a-zA-Z\s]+$', first_name): errors['first_name'] = "First name must contain only letters."
        if not re.match(r'^[a-zA-Z\s]+$', last_name): errors['last_name'] = "Last name must contain only letters."
        
        try:
            validate_email(email)
        except ValidationError:
            errors['email'] = "Invalid email format."
            
        if User.objects.filter(email=email).exclude(pk=vendor.user.pk).exists():
            errors['email'] = "Email is already in use."
            
        if Vendor.objects.filter(shopName=shop_name).exclude(pk=vendor.pk).exists():
            errors['shopName'] = "Shop name is already taken."
            
        if not business_phone.isdigit() or len(business_phone) != 10:
            errors['business_phone'] = "Phone number must be exactly 10 digits."

        if not errors:
            try:
                with transaction.atomic():
                    # Update User
                    vendor.user.first_name = first_name
                    vendor.user.last_name = last_name
                    vendor.user.email = email
                    vendor.user.save()
    
                    # Update Vendor
                    vendor.shopName = shop_name
                    vendor.shopAddress = request.POST.get('shopAddress')
                    vendor.business_phone = business_phone
                    vendor.description = request.POST.get('description')
                    
                    status = request.POST.get('status')
                    vendor.is_blocked = (status != 'Active')
    
                    # Handle Files
                    if request.FILES.get('profile_picture'):
                        vendor.profile_picture = request.FILES['profile_picture']
                    if request.FILES.get('panCard'):
                        vendor.panCard = request.FILES['panCard']
                    if request.FILES.get('adharCard'):
                        vendor.adharCard = request.FILES['adharCard']
                    vendor.save()
    
                    # Update Bank Details
                    if hasattr(vendor, 'bankdetail'):
                        bank = vendor.bankdetail
                        bank.bank_name = request.POST.get('bank_name')
                        bank.account_number = request.POST.get('account_number')
                        bank.ifsc_code = request.POST.get('ifsc_code')
                        bank.beneficiary_name = request.POST.get('beneficiary_name')
                        bank.save()
                    else:
                        BankDetail.objects.create(
                            vendor=vendor,
                            bank_name=request.POST.get('bank_name'),
                            account_number=request.POST.get('account_number'),
                            ifsc_code=request.POST.get('ifsc_code'),
                            beneficiary_name=request.POST.get('beneficiary_name')
                        )
    
                    messages.success(request, "Vendor updated successfully.")
                    return redirect('manage_vendors')
            except Exception as e:
                messages.error(request, f"Error updating vendor: {e}")
                
    else:
        # Initial Form Data
        form_data = {
            'first_name': vendor.user.first_name,
            'last_name': vendor.user.last_name,
            'email': vendor.user.email,
            'shopName': vendor.shopName,
            'shopAddress': vendor.shopAddress,
            'business_phone': vendor.business_phone,
            'description': vendor.description,
            'status': 'Active' if not vendor.is_blocked else 'Blocked',
            'bank_name': vendor.bankdetail.bank_name if hasattr(vendor, 'bankdetail') else '',
            'account_number': vendor.bankdetail.account_number if hasattr(vendor, 'bankdetail') else '',
            'ifsc_code': vendor.bankdetail.ifsc_code if hasattr(vendor, 'bankdetail') else '',
            'beneficiary_name': vendor.bankdetail.beneficiary_name if hasattr(vendor, 'bankdetail') else '',
        }
        
    return render(request, 'dashboard/user_form.html', {
        'action': 'Edit', 
        'role': 'Vendor', 
        'vendor_obj': vendor, # For file links
        'form_data': form_data,
        'errors': errors,
        'return_url': 'manage_vendors'
    })



@admin_required
def delete_vendor(request, pk):
    try:
        vendor = Vendor.objects.get(pk=pk)
        vendor.is_deleted = True
        vendor.save()
        # Also soft delete user? Usually yes.
        vendor.user.is_deleted = True
        vendor.user.save()
        messages.success(request, "Vendor deleted successfully.")
    except Vendor.DoesNotExist:
        messages.error(request, "Vendor not found.")
    except Exception as e:
        messages.error(request, f"Error deleting vendor: {e}")
    return redirect('manage_vendors')

@admin_required
def manage_categories(request):
    categories = [
        MockObj(pk=1, name="Sneakers", parent="Men", description="Casual daily wear shoes", status="Active", count=120),
        MockObj(pk=2, name="Running", parent="Sports", description="Performance running shoes", status="Active", count=85),
    ]
    return render(request, 'dashboard/manage_categories.html', {'categories': categories})

@admin_required
def add_category(request):
    parents = [MockObj(pk=10, name="Men"), MockObj(pk=11, name="Women"), MockObj(pk=12, name="Sports")]
    if request.method == "POST":
        messages.success(request, "Category added successfully (Mock)")
        return redirect('manage_categories')
    return render(request, 'dashboard/category_form.html', {'action': 'Add', 'parents': parents})

@admin_required
def edit_category(request, pk):
    parents = [MockObj(pk=10, name="Men"), MockObj(pk=11, name="Women"), MockObj(pk=12, name="Sports")]
    if request.method == "POST":
        messages.success(request, "Category updated successfully (Mock)")
        return redirect('manage_categories')
    category = MockObj(pk=pk, name="Sneakers", parent="Men", description="Casual daily wear shoes", status="Active")
    return render(request, 'dashboard/category_form.html', {'action': 'Edit', 'category': category, 'parents': parents})

@admin_required
def manage_products(request):
    products = [
        MockObj(pk=1, name="Nike Air Max", category="Sneakers", vendor="Kicks Palace", price="120.00", stock=50, status="Active", image="path/to/img", gender="M", is_trending=True),
        MockObj(pk=2, name="Adidas Ultraboost", category="Running", vendor="Spidey Shoes", price="180.00", stock=30, status="Active", image="path/to/img", gender="U", is_trending=False),
        MockObj(pk=3, name="Puma Suede", category="Sneakers", vendor="Kicks Palace", price="85.00", stock=0, status="Inactive", image="path/to/img", gender="W", is_trending=False),
    ]
    return render(request, 'dashboard/manage_products.html', {'products': products})

@admin_required
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

@admin_required
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

@admin_required
def manage_orders(request):
    orders = [
        MockObj(pk=1001, customer="Alice Smith", date="2023-10-20", total="$150", status="Processing", payment_status="Paid"),
        MockObj(pk=1002, customer="Bob Jones", date="2023-10-19", total="$220", status="Shipped", payment_status="Paid"),
        MockObj(pk=1003, customer="Charlie Brown", date="2023-10-18", total="$80", status="Cancelled", payment_status="Refunded"),
    ]
    vendors = [MockObj(pk=1, shopName="Kicks Palace"), MockObj(pk=2, shopName="Sporty Shoes")]
    return render(request, 'dashboard/manage_orders.html', {'orders': orders, 'vendors': vendors})

@admin_required
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

@admin_required
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

@admin_required
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

@admin_required
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

@admin_required
def manage_payments(request):
    payments = [
        MockObj(pk="PAY-12345", user="Alice Smith", amount="$150", method="Credit Card", status="Success", date="2023-10-20"),
        MockObj(pk="PAY-67890", user="Bob Jones", amount="$220", method="PayPal", status="Success", date="2023-10-19"),
        MockObj(pk="PAY-11223", user="Charlie Brown", amount="$80", method="Credit Card", status="Refunded", date="2023-10-18"),
    ]
    return render(request, 'dashboard/manage_payments.html', {'payments': payments})

@admin_required
def view_reviews(request):
    reviews = [
        MockObj(pk=1, product="Nike Air Max", user="John Doe", rating=5, comment="Love these shoes!", date="2023-10-21"),
        MockObj(pk=2, product="Adidas UltraBoost", user="Jane Smith", rating=4, comment="Very comfortable but expensive.", date="2023-10-20"),
    ]
    return render(request, 'dashboard/view_reviews.html', {'reviews': reviews})

@admin_required
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

@admin_required
def view_complaints(request):
    complaints = [
        MockObj(pk=1, user="Mike Ross", subject="Late Delivery", message="My order is 3 days late.", date="2023-10-21", status="Open"),
        MockObj(pk=2, user="Rachel Green", subject="Wrong Item", message="I received the wrong size.", date="2023-10-19", status="Resolved"),
    ]
    return render(request, 'dashboard/view_complaints.html', {'complaints': complaints})

@admin_required
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

@admin_required
def admin_profile(request):
    user = request.user
    if request.method == "POST":
        user.first_name = request.POST.get('first_name')
        user.last_name = request.POST.get('last_name')
        user.email = request.POST.get('email')
        try:
            user.save()
            messages.success(request, "Profile updated successfully.")
        except Exception as e:
            messages.error(request, f"Error updating profile: {e}")
            
    return render(request, 'dashboard/admin_profile.html', {'admin': user})

@admin_required
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