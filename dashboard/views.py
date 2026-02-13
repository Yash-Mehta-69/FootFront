from django.shortcuts import render, redirect, get_object_or_404
from django.db import transaction
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from datetime import datetime, timedelta
import firebase_admin
from firebase_admin import auth
from store.decorators import admin_required
from django.core.paginator import Paginator
from django.db.models import Q, Min, Count, Sum, Prefetch, F, Value
from django.db.models.functions import Concat, ExtractMonth
from utils.filters import get_date_range
from utils import panel_messages
from utils.exports import export_to_csv, export_to_pdf
from cart.models import Order, OrderItem, Shipment, ShipmentStatusHistory, Payment

@admin_required
def dashboard(request):
    # Base Queries
    customer_qs = Customer.objects.filter(is_deleted=False)
    product_qs = Product.objects.filter(is_deleted=False)
    order_qs = Order.objects.filter(is_deleted=False)
    payment_qs = Order.objects.filter(is_deleted=False, payment__status='completed')

    # Real Stats
    total_customers = customer_qs.count()
    total_products = product_qs.count()
    total_orders = order_qs.count()
    total_revenue_val = payment_qs.aggregate(total=Sum('total_amount'))['total'] or 0

    # Quick Growth Logic (Simplified: Current Month vs previous)
    now = timezone.now()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    prev_month_end = month_start - timedelta(seconds=1)
    prev_month_start = prev_month_end.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    curr_month_orders = Order.objects.filter(order_date__gte=month_start).count()
    prev_month_orders = Order.objects.filter(order_date__gte=prev_month_start, order_date__lt=month_start).count()
    
    orders_growth = 0
    if prev_month_orders > 0:
        orders_growth = ((curr_month_orders - prev_month_orders) / prev_month_orders) * 100

    # Graph Data: Weekly (Last 7 Days)
    weekly_labels = []
    weekly_data = []
    for i in range(6, -1, -1):
        day = now - timedelta(days=i)
        weekly_labels.append(day.strftime('%a'))
        day_revenue = Order.objects.filter(
            order_date__date=day.date(),
            payment__status='completed',
            is_deleted=False
        ).aggregate(total=Sum('total_amount'))['total'] or 0
        weekly_data.append(float(day_revenue))

    # Graph Data: Yearly (current year)
    yearly_labels = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    yearly_data = []
    for month in range(1, 13):
        month_revenue = Order.objects.filter(
            order_date__year=now.year,
            order_date__month=month,
            payment__status='completed',
            is_deleted=False
        ).aggregate(total=Sum('total_amount'))['total'] or 0
        yearly_data.append(float(month_revenue))

    stats = {
        'total_users': total_customers,
        'users_growth': 5.4, # Keep aesthetic growth for now or implement user growth
        'total_products': total_products,
        'products_growth': 2.1,
        'total_orders': total_orders,
        'orders_growth': round(orders_growth, 1),
        'total_revenue': f"₹{int(total_revenue_val):,}",
        'revenue_growth': 8.2,
        'graph_data': {
            'weekly': {'labels': weekly_labels, 'data': weekly_data},
            'yearly': {'labels': yearly_labels, 'data': yearly_data}
        }
    }
    
    # Real Recent Orders
    recent_orders_raw = Order.objects.filter(is_deleted=False).select_related(
        'customer', 'customer__user', 'payment'
    ).prefetch_related('items__product_variant__product').order_by('-order_date')[:5]

    recent_orders = []
    for o in recent_orders_raw:
        # Get first item name or summary
        items = list(o.items.all())
        product_summary = items[0].product_variant.product.name if items else "No Items"
        if len(items) > 1:
            product_summary += f" (+{len(items)-1} more)"
            
        status_map = {
            'completed': 'success',
            'pending': 'warning',
            'failed': 'danger'
        }
        
        recent_orders.append({
            'pk': f"#ORD-{o.pk}",
            'customer_name': f"{o.customer.user.first_name} {o.customer.user.last_name}",
            'product': product_summary,
            'date': o.order_date.strftime("%b %d, %Y"),
            'status': o.payment.get_status_display() if o.payment else "Unpaid",
            'amount': f"₹{o.total_amount:,}",
            'status_class': status_map.get(o.payment.status if o.payment else 'pending', 'warning')
        })
    
    context = {
        'stats': stats,
        'recent_orders': recent_orders_raw,
    }
    return render(request, 'dashboard/admin_dashboard.html', context)

from store.models import Customer, Category, Product, ProductVariant, Size, Color, AttributeRequest, Review ,Complaint
from store.forms import CategoryForm, ProductForm, SizeForm, ColorForm, CustomerAdminForm, VendorAdminForm
from vendor.models import Vendor

@admin_required
def manage_customers(request):
    q = request.GET.get('q', '')
    status = request.GET.get('status', '')
    
    customers = Customer.objects.select_related('user').filter(is_deleted=False)
    
    if q:
        customers = customers.filter(
            Q(user__first_name__icontains=q) |
            Q(user__last_name__icontains=q) |
            Q(user__email__icontains=q) |
            Q(phone__icontains=q)
        )
        
    if status:
        customers = customers.filter(is_blocked=(status == 'Blocked'))
        
    customer_fields = [
        ('user.get_full_name', 'Full Name'),
        ('user.email', 'Email'),
        ('phone', 'Phone'),
        ('is_blocked', 'Is Blocked'),
        ('created_at', 'Joined Date')
    ]

    if request.GET.get('export') == 'csv':
        return export_to_csv(customers, 'customers', customer_fields)
    elif request.GET.get('export') == 'pdf':
        return export_to_pdf(customers, 'customers', customer_fields)

    context = {
        'customers': customers,
        'search_query': q,
        'current_status': status
    }
    
    if request.GET.get('ajax') == '1':
        return render(request, 'dashboard/partials/customer_table.html', context)
        
    return render(request, 'dashboard/manage_customers.html', context)

@admin_required
def add_customer(request):
    if request.method == "POST":
        form = CustomerAdminForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    # Clear any soft-deleted orphans to avoid collisions
                    import time
                    ts = int(time.time())
                    User.objects.filter(email=form.cleaned_data['email'], is_deleted=True).update(
                        email=Concat(Value(f"deleted_{ts}_"), F('email'))
                    )
                    
                    user = User.objects.create_user(
                        email=form.cleaned_data['email'],
                        password=form.cleaned_data['password'],
                        first_name=form.cleaned_data['first_name'],
                        last_name=form.cleaned_data['last_name'],
                        role='customer'
                    )
                Customer.objects.create(
                    user=user, 
                    phone=form.cleaned_data['phone'],
                    is_blocked=(form.cleaned_data['status'] != 'Active')
                )
                panel_messages.add_admin_message(request, 'success', "Customer added successfully.")
                return redirect('manage_customers')
            except Exception as e:
                panel_messages.add_admin_message(request, 'error', f"Error adding customer: {e}")
    else:
        form = CustomerAdminForm()
        
    return render(request, 'dashboard/user_form.html', {
        'action': 'Add', 
        'role': 'Customer', 
        'return_url': 'manage_customers',
        'form': form
    })

@admin_required
def edit_customer(request, pk):
    try:
        customer = Customer.objects.select_related('user').get(pk=pk)
    except Customer.DoesNotExist:
        panel_messages.add_admin_message(request, 'error', "Customer not found.")
        return redirect('manage_customers')

    if request.method == "POST":
        form = CustomerAdminForm(request.POST, user=customer.user)
        if form.is_valid():
            try:
                with transaction.atomic():
                    # Clear any soft-deleted orphans to avoid collisions
                    import time
                    ts = int(time.time())
                    User.objects.filter(email=form.cleaned_data['email'], is_deleted=True).exclude(pk=customer.user.pk).update(
                        email=Concat(Value(f"deleted_{ts}_"), F('email'))
                    )
                    
                    # Update User fields
                    customer.user.first_name = form.cleaned_data['first_name']
                    customer.user.last_name = form.cleaned_data['last_name']
                    customer.user.email = form.cleaned_data['email']
                    customer.user.save()
                    
                    # Update Customer fields
                    customer.phone = form.cleaned_data['phone']
                    customer.is_blocked = (form.cleaned_data['status'] != 'Active')
                    customer.save()
                    
                    panel_messages.add_admin_message(request, 'success', "Customer updated successfully.")
                    return redirect('manage_customers')
            except Exception as e:
                panel_messages.add_admin_message(request, 'error', f"Error updating customer: {e}")
    else:
        # Initial Form Data
        initial_data = {
            'first_name': customer.user.first_name,
            'last_name': customer.user.last_name,
            'email': customer.user.email,
            'phone': customer.phone,
            'status': 'Active' if not customer.is_blocked else 'Blocked'
        }
        form = CustomerAdminForm(initial=initial_data, user=customer.user)

    return render(request, 'dashboard/user_form.html', {
        'action': 'Edit', 
        'role': 'Customer', 
        'customer_obj': customer,
        'form': form,
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
        customer.firebase_uid = None
        customer.save()

        # Rename user email to free it up
        import time
        ts = int(time.time())
        customer.user.email = f"deleted_{ts}_{customer.user.email}"
        customer.user.is_deleted = True
        customer.user.save()
        
        panel_messages.add_admin_message(request, 'success', "Customer deleted successfully.")
    except Customer.DoesNotExist:
        panel_messages.add_admin_message(request, 'error', "Customer not found.")
    except Exception as e:
        panel_messages.add_admin_message(request, 'error', f"Error deleting customer: {e}")
        
    return redirect('manage_customers')

@admin_required
def detail_customer(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    return render(request, 'dashboard/customer_detail.html', {'customer': customer})

from vendor.models import Vendor, BankDetail
from django.db import transaction
from store.models import User

@admin_required
def manage_vendors(request):
    q = request.GET.get('q', '')
    status = request.GET.get('status', '')
    
    vendors = Vendor.objects.select_related('user', 'bankdetail').filter(is_deleted=False)
    
    if q:
        vendors = vendors.filter(
            Q(shopName__icontains=q) |
            Q(user__first_name__icontains=q) |
            Q(user__last_name__icontains=q) |
            Q(user__email__icontains=q) |
            Q(business_phone__icontains=q)
        ).distinct()
        
    if status:
        vendors = vendors.filter(is_blocked=(status == 'Blocked'))

    vendor_fields = [
        ('shopName', 'Shop Name'),
        ('description', 'Shop Description'),
        ('user.get_full_name', 'Vendor Name'),
        ('user.email', 'Email'),
        ('business_phone', 'Phone'),
        ('bankdetail.bank_name', 'Bank Name'),
        ('bankdetail.account_number', 'Account Number'),
        ('bankdetail.ifsc_code', 'IFSC Code'),
        ('is_blocked', 'Is Blocked'),
        ('created_at', 'Joined At')
    ]

    if request.GET.get('export') == 'csv':
        return export_to_csv(vendors, 'vendors', vendor_fields)
    elif request.GET.get('export') == 'pdf':
        return export_to_pdf(vendors, 'vendors', vendor_fields)

    context = {
        'vendors': vendors,
        'search_query': q,
        'current_status': status
    }
    
    if request.GET.get('ajax') == '1':
        return render(request, 'dashboard/partials/vendor_table.html', context)
        
    return render(request, 'dashboard/manage_vendors.html', context)

@admin_required
def add_vendor(request):
    if request.method == "POST":
        form = VendorAdminForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                with transaction.atomic():
                    # Clear any soft-deleted orphans to avoid collisions
                    import time
                    ts = int(time.time())
                    
                    User.objects.filter(email=form.cleaned_data['email'], is_deleted=True).update(
                        email=Concat(Value(f"deleted_{ts}_"), F('email'))
                    )
                    
                    Vendor.objects.filter(shopName=form.cleaned_data['shopName'], is_deleted=True).update(
                        shopName=Concat(Value(f"deleted_{ts}_"), F('shopName'))
                    )
                    
                    # 1. Create User
                    user = User.objects.create_user(
                        email=form.cleaned_data['email'],
                        password=form.cleaned_data['password'],
                        first_name=form.cleaned_data['first_name'],
                        last_name=form.cleaned_data['last_name'],
                        role='vendor'
                    )
                    
                    # 2. Create Vendor Profile
                    vendor = Vendor.objects.create(
                        user=user,
                        shopName=form.cleaned_data['shopName'],
                        shopAddress=form.cleaned_data['shopAddress'],
                        business_phone=form.cleaned_data['business_phone'],
                        description=form.cleaned_data.get('description'),
                        is_blocked=(form.cleaned_data['status'] != 'Active'),
                        profile_picture=form.cleaned_data.get('profile_picture'),
                        panCard=form.cleaned_data.get('panCard'),
                        adharCard=form.cleaned_data.get('adharCard')
                    )
                    
                    # 3. Create Bank Details
                    BankDetail.objects.create(
                        vendor=vendor,
                        bank_name=form.cleaned_data['bank_name'],
                        account_number=form.cleaned_data['account_number'],
                        ifsc_code=form.cleaned_data['ifsc_code'],
                        beneficiary_name=form.cleaned_data['beneficiary_name']
                    )
                    
                    panel_messages.add_admin_message(request, 'success', "Vendor added successfully.")
                    return redirect('manage_vendors')
            except Exception as e:
                panel_messages.add_admin_message(request, 'error', f"Error adding vendor: {e}")
    else:
        form = VendorAdminForm()

    return render(request, 'dashboard/user_form.html', {
        'action': 'Add', 
        'role': 'Vendor', 
        'return_url': 'manage_vendors',
        'form': form
    })

@admin_required
def edit_vendor(request, pk):
    try:
        vendor = Vendor.objects.select_related('user', 'bankdetail').get(pk=pk)
    except Vendor.DoesNotExist:
        panel_messages.add_admin_message(request, 'error', "Vendor not found.")
        return redirect('manage_vendors')

    if request.method == "POST":
        form = VendorAdminForm(request.POST, request.FILES, user=vendor.user, vendor=vendor)
        if form.is_valid():
            try:
                with transaction.atomic():
                    # Clear any soft-deleted orphans to avoid collisions
                    import time
                    ts = int(time.time())
                    
                    User.objects.filter(email=form.cleaned_data['email'], is_deleted=True).exclude(pk=vendor.user.pk).update(
                        email=Concat(Value(f"deleted_{ts}_"), F('email'))
                    )
                    
                    Vendor.objects.filter(shopName=form.cleaned_data['shopName'], is_deleted=True).exclude(pk=vendor.pk).update(
                        shopName=Concat(Value(f"deleted_{ts}_"), F('shopName'))
                    )
                    
                    # Update User
                    vendor.user.first_name = form.cleaned_data['first_name']
                    vendor.user.last_name = form.cleaned_data['last_name']
                    vendor.user.email = form.cleaned_data['email']
                    vendor.user.save()
    
                    # Update Vendor
                    vendor.shopName = form.cleaned_data['shopName']
                    vendor.shopAddress = form.cleaned_data['shopAddress']
                    vendor.business_phone = form.cleaned_data['business_phone']
                    vendor.description = form.cleaned_data.get('description')
                    vendor.is_blocked = (form.cleaned_data['status'] != 'Active')
    
                    if form.cleaned_data.get('profile_picture'):
                        vendor.profile_picture = form.cleaned_data['profile_picture']
                    if form.cleaned_data.get('panCard'):
                        vendor.panCard = form.cleaned_data['panCard']
                    if form.cleaned_data.get('adharCard'):
                        vendor.adharCard = form.cleaned_data['adharCard']
                    vendor.save()
    
                    # Update Bank Details
                    bank, created = BankDetail.objects.get_or_create(vendor=vendor)
                    bank.bank_name = form.cleaned_data['bank_name']
                    bank.account_number = form.cleaned_data['account_number']
                    bank.ifsc_code = form.cleaned_data['ifsc_code']
                    bank.beneficiary_name = form.cleaned_data['beneficiary_name']
                    bank.save()
    
                    panel_messages.add_admin_message(request, 'success', "Vendor updated successfully.")
                    return redirect('manage_vendors')
            except Exception as e:
                panel_messages.add_admin_message(request, 'error', f"Error updating vendor: {e}")
    else:
        # Initial Form Data
        initial_data = {
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
        form = VendorAdminForm(initial=initial_data, user=vendor.user, vendor=vendor)
        
    return render(request, 'dashboard/user_form.html', {
        'action': 'Edit', 
        'role': 'Vendor', 
        'vendor_obj': vendor,
        'form': form,
        'return_url': 'manage_vendors'
    })



@admin_required
def delete_vendor(request, pk):
    try:
        vendor = Vendor.objects.get(pk=pk)
        
        # Rename unique fields to free them up
        import time
        ts = int(time.time())
        
        vendor.shopName = f"deleted_{ts}_{vendor.shopName}"
        vendor.is_deleted = True
        vendor.save()
        
        vendor.user.email = f"deleted_{ts}_{vendor.user.email}"
        vendor.user.is_deleted = True
        vendor.user.save()
        
        panel_messages.add_admin_message(request, 'success', "Vendor deleted successfully.")
    except Vendor.DoesNotExist:
        panel_messages.add_admin_message(request, 'error', "Vendor not found.")
    except Exception as e:
        panel_messages.add_admin_message(request, 'error', f"Error deleting vendor: {e}")
    return redirect('manage_vendors')

@admin_required
def detail_vendor(request, pk):
    vendor = get_object_or_404(Vendor.objects.select_related('user', 'bankdetail'), pk=pk)
    return render(request, 'dashboard/vendor_detail.html', {'vendor': vendor})

@admin_required
def manage_categories(request):
    q = request.GET.get('q', '')
    sort = request.GET.get('sort', 'name_asc')
    
    categories = Category.objects.filter(is_deleted=False).select_related('parent_category')
    
    if sort == 'name_desc':
        categories = categories.order_by('-name')
    elif sort == 'products_high':
        categories = categories.annotate(product_count=Count('product')).order_by('-product_count')
    else: # name_asc
        categories = categories.order_by('name')

    if request.GET.get('export') == 'csv':
        fields = [
            ('name', 'Category Name'),
            ('parent_category.name', 'Parent Category'),
            ('description', 'Description')
        ]
        return export_to_csv(categories, 'categories', fields)
    elif request.GET.get('export') == 'pdf':
        fields = [
            ('name', 'Category Name'),
            ('parent_category.name', 'Parent Category'),
            ('description', 'Description')
        ]
        return export_to_pdf(categories, 'categories', fields)
        
    context = {
        'categories': categories,
        'sort': sort,
        'q': q, # Passed if we ever re-add it, but good for base script
    }

    if request.GET.get('ajax') == '1':
        return render(request, 'dashboard/partials/category_table.html', context)
        
    return render(request, 'dashboard/manage_categories.html', context)

@admin_required
def add_category(request):
    if request.method == "POST":
        form = CategoryForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            panel_messages.add_admin_message(request, 'success', "Category added successfully.")
            return redirect('manage_categories')
        else:
            panel_messages.add_admin_message(request, 'error', f"Error adding category: {form.errors}")
    else:
        form = CategoryForm()
    return render(request, 'dashboard/category_form.html', {'action': 'Add', 'form': form})

@admin_required
def edit_category(request, pk):
    try:
        category = Category.objects.get(pk=pk)
    except Category.DoesNotExist:
        panel_messages.add_admin_message(request, 'error', "Category not found.")
        return redirect('manage_categories')

    if request.method == "POST":
        form = CategoryForm(request.POST, request.FILES, instance=category)
        if form.is_valid():
            form.save()
            panel_messages.add_admin_message(request, 'success', "Category updated successfully.")
            return redirect('manage_categories')
        else:
            panel_messages.add_admin_message(request, 'error', f"Error updating category: {form.errors}")
    else:
        form = CategoryForm(instance=category)
    return render(request, 'dashboard/category_form.html', {'action': 'Edit', 'category': category, 'form': form})

@admin_required
def delete_category(request, pk):
    try:
        category = Category.objects.get(pk=pk)
        category.is_deleted = True
        category.save()
        panel_messages.add_admin_message(request, 'success', "Category soft-deleted successfully.")
    except Category.DoesNotExist:
        panel_messages.add_admin_message(request, 'error', "Category not found.")
    return redirect('manage_categories')

@admin_required
def detail_category(request, pk):
    category = get_object_or_404(Category, pk=pk)
    return render(request, 'dashboard/category_detail.html', {'category': category})

@admin_required
def manage_products(request):
    
    # Prefetch only active variants to avoid showing deleted ones (which solves the price not updating issue)
    active_variants_prefetch = Prefetch(
        'productvariant_set',
        queryset=ProductVariant.objects.filter(is_deleted=False),
        to_attr='active_variants'
    )
    
    products = Product.objects.filter(is_deleted=False).select_related('vendor', 'category').prefetch_related(active_variants_prefetch)
    
    # Filter by Category
    category_id = request.GET.get('category')
    if category_id:
        products = products.filter(category_id=category_id)

    # Filter by Vendor
    vendor_id = request.GET.get('vendor')
    if vendor_id:
        products = products.filter(vendor_id=vendor_id)

    # Search
    query = request.GET.get('q')
    if query:
        products = products.filter(Q(name__icontains=query) | Q(description__icontains=query))

    # Sort
    sort_by = request.GET.get('sort')
    if sort_by == 'price_low':
        products = products.annotate(min_price=Min('productvariant__price')).order_by('min_price')
    elif sort_by == 'price_high':
        products = products.annotate(min_price=Min('productvariant__price')).order_by('-min_price')
    elif sort_by == 'date_oldest':
        products = products.order_by('created_at')
    else: # Default: Newest first
        products = products.order_by('-created_at')

    # Pagination
    paginator = Paginator(products, 10)
    page_number = request.GET.get('page')
    products_page = paginator.get_page(page_number)

    product_fields = [
        ('product.name', 'Product Name'),
        ('product.category.name', 'Category'),
        ('product.vendor.shopName', 'Vendor'),
        ('size.size_label', 'Size'),
        ('color.name', 'Color'),
        ('price', 'Price'),
        ('stock', 'Stock'),
        ('product.gender', 'Gender'),
        ('product.is_trending', 'Is Trending'),
        ('product.created_at', 'Date Created')
    ]

    if request.GET.get('export') == 'csv':
        # Enhanced export: One row per variant
        variants = ProductVariant.objects.filter(product__in=products, is_deleted=False).select_related(
            'product', 'product__vendor', 'product__category', 'size', 'color'
        ).order_by('product__name', 'size__size_label')
        return export_to_csv(variants, 'products', product_fields)
    elif request.GET.get('export') == 'pdf':
        variants = ProductVariant.objects.filter(product__in=products, is_deleted=False).select_related(
            'product', 'product__vendor', 'product__category', 'size', 'color'
        ).order_by('product__name', 'size__size_label')
        return export_to_pdf(variants, 'products', product_fields)

    context = {
        'products': products_page,
        'categories': Category.objects.filter(is_deleted=False),
        'vendors': Vendor.objects.filter(is_deleted=False),
        'search_query': query,
        'current_category': int(category_id) if category_id else None,
        'current_vendor': int(vendor_id) if vendor_id else None,
        'current_sort': sort_by,
    }
    if request.GET.get('ajax') == '1':
        return render(request, 'dashboard/partials/product_table.html', context)
        
    return render(request, 'dashboard/manage_products.html', context)

@admin_required
def add_product(request):
    if request.method == "POST":
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                with transaction.atomic():
                    product = form.save()
                    
                    # Handle Variants
                    sizes = request.POST.getlist('variant_size[]')
                    colors = request.POST.getlist('variant_color[]')
                    prices = request.POST.getlist('variant_price[]')
                    stocks = request.POST.getlist('variant_stock[]')
                    
                    # For images, assuming simple handling for provided rows
                    # Note: This simple loop assumes parallel arrays match. 
                    # Browsers send empty strings for empty text inputs, so lengths match.
                    # But files are different. We will try to map by index if we update template or just SKIP images for variants for now to avoid crashes if arrays misalign.
                    # Upgrading template to indexed names is best, but for now we implement basic saving.
                    
                    variant_count = 0
                    for i in range(len(sizes)):
                        if sizes[i] and colors[i] and prices[i] and stocks[i]: # Ensure valid row
                            variant_image = request.FILES.get(f'variant_image_{i}')
                            
                            ProductVariant.objects.create(
                                product=product,
                                size_id=sizes[i],
                                color_id=colors[i],
                                price=prices[i],
                                stock=stocks[i],
                                image=variant_image if variant_image else product.product_image
                            )
                            variant_count += 1
                    
                    if variant_count == 0:
                        raise ValueError("At least one valid variant (Size, Color, Price, Stock) is required.")

                    panel_messages.add_admin_message(request, 'success', "Product added successfully.")
                    return redirect('manage_products')
            except Exception as e:
                panel_messages.add_admin_message(request, 'error', f"Error creating product: {e}")
        else:
             panel_messages.add_admin_message(request, 'error', f"Form error: {form.errors}")
    else:
        form = ProductForm()

    context = {
        'action': 'Add',
        'form': form,
        'vendors': Vendor.objects.filter(is_deleted=False, is_blocked=False),
        'categories': Category.objects.filter(is_deleted=False),
        'sizes': Size.objects.all(),
        'colors': Color.objects.all(),
    }
    return render(request, 'dashboard/product_form.html', context)

@admin_required
def edit_product(request, pk):
    try:
        product = Product.objects.get(pk=pk)
    except Product.DoesNotExist:
        panel_messages.add_admin_message(request, 'error', "Product not found.")
        return redirect('manage_products')

    if request.method == "POST":
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            try:
                with transaction.atomic():
                    product = form.save()
                    
                    # 1. Get Lists from POST
                    variant_ids = request.POST.getlist('variant_id[]')
                    sizes = request.POST.getlist('variant_size[]')
                    colors = request.POST.getlist('variant_color[]')
                    prices = request.POST.getlist('variant_price[]')
                    stocks = request.POST.getlist('variant_stock[]')

                    # 2. Identify Kept IDs to detect Deletions
                    # Filter out empty strings from variant_ids (which represent new rows)
                    kept_ids = [int(vid) for vid in variant_ids if vid and vid.isdigit()]

                    # 3. Soft Delete Removed Variants
                    # Any variant currently active for this product that is NOT in kept_ids should be deleted
                    product.productvariant_set.filter(is_deleted=False).exclude(id__in=kept_ids).update(is_deleted=True)

                    # 4. Loop and Upsert (Update or Insert)
                    variant_count = 0
                    for i in range(len(sizes)):
                        if sizes[i] and colors[i] and prices[i] and stocks[i]:
                             current_id = variant_ids[i] if i < len(variant_ids) and variant_ids[i].isdigit() else None
                             variant_image = request.FILES.get(f'variant_image_{i}')
                             
                             if current_id:
                                 # UPDATE existing
                                 variant = ProductVariant.objects.get(pk=current_id, product=product)
                                 variant.size_id = sizes[i]
                                 variant.color_id = colors[i]
                                 variant.price = prices[i]
                                 variant.stock = stocks[i]
                                 if variant_image:
                                     variant.image = variant_image
                                 variant.save()
                                 variant_count += 1
                             else:
                                 # CREATE new
                                 ProductVariant.objects.create(
                                    product=product,
                                    size_id=sizes[i],
                                    color_id=colors[i],
                                    price=prices[i],
                                    stock=stocks[i],
                                    image=variant_image if variant_image else product.product_image
                                )
                                 variant_count += 1
                    
                    if variant_count == 0:
                        raise ValueError("At least one valid variant (Size, Color, Price, Stock) is required.")
                                
                    panel_messages.add_admin_message(request, 'success', "Product updated successfully.")
                    return redirect('manage_products')
            except Exception as e:
                import traceback
                traceback.print_exc()
                panel_messages.add_admin_message(request, 'error', f"Error updating product: {e}")
    else:
        form = ProductForm(instance=product)

    # Pre-fetch variants for template
    existing_variants = product.productvariant_set.filter(is_deleted=False)

    context = {
        'action': 'Edit',
        'form': form,
        'product': product, # For template access to instance
        'variants': existing_variants,
        'vendors': Vendor.objects.filter(is_deleted=False),
        'categories': Category.objects.filter(is_deleted=False),
        'sizes': Size.objects.all(),
        'colors': Color.objects.all(),
    }
    return render(request, 'dashboard/product_form.html', context)

@admin_required
def delete_product(request, pk):
    try:
        product = Product.objects.get(pk=pk)
        product.is_deleted = True
        product.save()
        panel_messages.add_admin_message(request, 'success', "Product soft-deleted successfully.")
    except Product.DoesNotExist:
        panel_messages.add_admin_message(request, 'error', "Product not found.")
    return redirect('manage_products')

@admin_required
def detail_product(request, pk):
    product = get_object_or_404(Product.objects.select_related('vendor', 'category').prefetch_related('productvariant_set'), pk=pk)
    return render(request, 'dashboard/product_detail.html', {'product': product})

@admin_required
def manage_orders(request):
    # Filtering parameters
    q = request.GET.get('q', '')
    vendor_id = request.GET.get('vendor', '')
    sort = request.GET.get('sort', 'date_newest')
    date_filter = request.GET.get('date_filter', 'all')
    start_date_str = request.GET.get('start_date', '')
    end_date_str = request.GET.get('end_date', '')
    
    start_date, end_date = get_date_range(date_filter, start_date_str, end_date_str)
    
    # Base queryset
    orders = Order.objects.filter(is_deleted=False).select_related(
        'customer', 'customer__user', 'payment', 'shipping_address'
    ).prefetch_related(
        Prefetch(
            'items',
            queryset=OrderItem.objects.filter(is_deleted=False).select_related(
                'product_variant', 'product_variant__product',
                'product_variant__size', 'product_variant__color', 'shipment'
            ),
            to_attr='all_items'
        )
    )

    # Date Filtering
    if start_date:
        orders = orders.filter(order_date__gte=start_date)
    if end_date:
        orders = orders.filter(order_date__lte=end_date)

    # Searching
    if q:
        clean_id = q.upper().replace('#ORD-', '').strip()
        if clean_id.isdigit():
            orders = orders.filter(pk=int(clean_id))
        else:
            orders = orders.filter(
                Q(customer__user__first_name__icontains=q) |
                Q(customer__user__last_name__icontains=q) |
                Q(customer__user__email__icontains=q)
            )

    # Filter by Vendor (Show orders that contain at least one item from this vendor)
    if vendor_id:
        orders = orders.filter(items__product_variant__product__vendor_id=vendor_id).distinct()

    # Sorting
    if sort == 'date_newest':
        orders = orders.order_by('-order_date')
    elif sort == 'date_oldest':
        orders = orders.order_by('order_date')

    order_fields = [
        ('pk', 'Order ID'),
        ('customer.user.get_full_name', 'Customer'),
        ('customer.user.email', 'Email'),
        ('get_items_display', 'Items'),
        ('total_amount', 'Amount'),
        ('admin_earnings', 'Earnings (7%)'),
        ('payment_info', 'Payment Details'),
        ('order_date', 'Date'),
        ('shipping_address.address_line1', 'Address Line 1'),
        ('shipping_address.address_line2', 'Address Line 2'),
        ('shipping_address.city', 'City'),
        ('shipping_address.state', 'State'),
        ('shipping_address.postal_code', 'Pin Code')
    ]

    if request.GET.get('export') == 'csv':
        return export_to_csv(orders, 'orders', order_fields)
    elif request.GET.get('export') == 'pdf':
        return export_to_pdf(orders, 'orders', order_fields)
    
    # Pagination
    paginator = Paginator(orders, 10)
    page_number = request.GET.get('page')
    orders_page = paginator.get_page(page_number)

    # Attach Vendor Display Info
    for order in orders_page:
        vendors = {item.product_variant.product.vendor.shopName for item in order.all_items}
        if not vendors:
            order.vendor_display_text = "No Vendor"
        elif len(vendors) == 1:
            order.vendor_display_text = list(vendors)[0]
        else:
            # If 2 vendors, show both. If more, show "Multi-Vendor" or "A, B +X"
            # User likely wants clarity. Let's show first 2 names then +X
            sorted_vendors = sorted(list(vendors))
            if len(sorted_vendors) <= 2:
                order.vendor_display_text = ", ".join(sorted_vendors)
            else:
                order.vendor_display_text = f"{sorted_vendors[0]}, {sorted_vendors[1]} (+{len(vendors)-2})"
    
    context = {
        'orders': orders_page,
        'vendors': Vendor.objects.filter(is_deleted=False),
        'search_query': q,
        'current_vendor': int(vendor_id) if vendor_id and vendor_id.isdigit() else '',
        'current_sort': sort,
        'current_filter': date_filter,
        'start_date': start_date_str,
        'end_date': end_date_str
    }
    
    if request.GET.get('ajax') == '1':
        return render(request, 'dashboard/partials/order_table.html', context)
        
    return render(request, 'dashboard/manage_orders.html', context)

@admin_required
def admin_edit_order(request, pk):
    order = get_object_or_404(Order, pk=pk, is_deleted=False)
    
    if request.method == "POST":
        # Note: Administrative edits to existing orders are limited to payment/status meta
        # Complex changes (adding/removing items) usually require a new order.
        new_status = request.POST.get('status') # This might refer to payment status in this context
        if order.payment:
            order.payment.status = new_status
            order.payment.save()
            
        panel_messages.add_admin_message(request, 'success', f"Order #{pk} details updated professionally.")
        return redirect('manage_orders')
        
    return render(request, 'dashboard/edit_order.html', {'order': order})

@admin_required
def order_detail(request, pk):
    order = get_object_or_404(
        Order.objects.filter(is_deleted=False).select_related(
            'customer', 'customer__user', 'shipping_address', 'payment'
        ).prefetch_related(
            Prefetch(
                'items',
                queryset=OrderItem.objects.filter(is_deleted=False).select_related(
                    'product_variant', 'product_variant__product',
                    'product_variant__size', 'product_variant__color', 'shipment'
                ),
                to_attr='all_items'
            )
        ),
        pk=pk
    )
    return render(request, 'dashboard/order_detail.html', {'order': order})

@admin_required
def manage_shipments(request):
    # Filtering parameters
    q = request.GET.get('q', '')
    status = request.GET.get('status', '')
    vendor_id = request.GET.get('vendor', '')
    order_id = request.GET.get('order_id', '')
    sort = request.GET.get('sort', 'shipped_newest')
    date_filter = request.GET.get('date_filter', 'all')
    start_date_str = request.GET.get('start_date', '')
    end_date_str = request.GET.get('end_date', '')
    
    start_date, end_date = get_date_range(date_filter, start_date_str, end_date_str)
    
    # Base queryset
    shipments = Shipment.objects.filter(is_deleted=False).select_related(
        'order_item', 'order_item__order', 'vendor',
        'order_item__product_variant', 'order_item__product_variant__product'
    )

    # Date Filtering
    if start_date:
        shipments = shipments.filter(order_item__order__order_date__gte=start_date)
    if end_date:
        shipments = shipments.filter(order_item__order__order_date__lte=end_date)
    
    # Searching
    if q:
        shipments = shipments.filter(
            Q(tracking_number__icontains=q) |
            Q(order_item__product_variant__product__name__icontains=q)
        )
        
    # Order ID Filter
    if order_id:
        try:
            clean_id = order_id.upper().replace('#ORD-', '').strip()
            if clean_id.isdigit():
                shipments = shipments.filter(order_item__order__pk=int(clean_id))
            else:
                shipments = shipments.filter(order_item__order__pk__icontains=clean_id)
        except:
            pass

    # Status Filter
    if status:
        shipments = shipments.filter(status=status)
        
    # Vendor Filter
    if vendor_id:
        shipments = shipments.filter(vendor_id=vendor_id)
        
    # Sorting
    if sort == 'shipped_newest':
        shipments = shipments.order_by('-shipped_at')
    elif sort == 'shipped_oldest':
        shipments = shipments.order_by('shipped_at')
    elif sort == 'delivery_newest':
        shipments = shipments.order_by('-expected_delivery')
    elif sort == 'delivery_oldest':
        shipments = shipments.order_by('expected_delivery')
        
    if request.GET.get('export'):
        # Prepare data for export with merged item details
        # MUST convert to list to persist runtime attributes like item_display
        shipments_list = list(shipments)
        for shipment in shipments_list:
            item = shipment.order_item
            variant = item.product_variant
            shipment.item_display = f"{item.quantity} x {variant.product.name} ({variant.size.size_label}/{variant.color.name})"

        shipment_fields = [
            ('order_item.order.pk', 'Order ID'),
            ('order_item.order.customer.user.get_full_name', 'Customer'),
            ('vendor.shopName', 'Vendor'),
            ('tracking_number', 'Tracking #'),
            ('courier_name', 'Courier'),
            ('item_display', 'Items'),
            ('status', 'Status'),
            ('shipped_at', 'Shipped Date'),
            ('expected_delivery', 'Expected Delivery')
        ]

        if request.GET.get('export') == 'csv':
            return export_to_csv(shipments_list, 'shipments', shipment_fields)
        elif request.GET.get('export') == 'pdf':
            return export_to_pdf(shipments_list, 'shipments', shipment_fields)

    # Pagination
    paginator = Paginator(shipments, 10)
    page_number = request.GET.get('page')
    shipments_page = paginator.get_page(page_number)
    
    # Get all unique Order IDs for the datalist
    admin_order_ids = OrderItem.objects.filter(is_deleted=False).values_list('order_id', flat=True).distinct().order_by('-order_id')
    
    context = {
        'shipments': shipments_page,
        'vendors': Vendor.objects.filter(is_deleted=False),
        'admin_order_ids': admin_order_ids,
        'search_query': q,
        'order_id_filter': order_id,
        'current_status': status,
        'current_vendor': int(vendor_id) if vendor_id and vendor_id.isdigit() else '',
        'current_sort': sort,
        'current_filter': date_filter,
        'start_date': start_date_str,
        'end_date': end_date_str,
        'status_choices': Shipment.STATUS_CHOICES
    }

    if request.GET.get('ajax') == '1':
        return render(request, 'dashboard/partials/shipment_table.html', context)
        
    return render(request, 'dashboard/manage_shipments.html', context)

@admin_required
def admin_update_shipment_status(request, pk):
    shipment = get_object_or_404(Shipment, pk=pk, is_deleted=False)
    
    if request.method == 'POST':
        try:
            status = request.POST.get('status')
            courier = request.POST.get('courier_name')
            tracking = request.POST.get('tracking_number')

            if status == 'in_transit' and (not courier or not tracking):
                panel_messages.add_admin_message(request, 'error', "Courier and Tracking Number are required for In Transit status.")
            else:
                # Lifecycle Enforcement: Define rank for statuses to prevent reverting
                rank = {'preparing': 1, 'shipped': 2, 'in_transit': 3, 'delivered': 4}
                current_rank = rank.get(shipment.status, 0)
                new_rank = rank.get(status, 0)
                
                if new_rank < current_rank:
                    panel_messages.add_admin_message(request, 'error', f"Admin Override: Cannot revert status from {shipment.get_status_display()} to {status.title()}.")
                    return redirect(request.META.get('HTTP_REFERER', 'manage_shipments'))

                shipment.status = status
                if courier: shipment.courier_name = courier
                if tracking: shipment.tracking_number = tracking
                
                if status == 'shipped' and not shipment.shipped_at:
                    shipment.shipped_at = timezone.now()
                
                if status == 'shipped' and not shipment.expected_delivery:
                    shipment.expected_delivery = (timezone.now() + timedelta(days=7)).date()
                    
                shipment.save()
                
                # Log History
                ShipmentStatusHistory.objects.create(
                    shipment=shipment,
                    status=status.replace('_', ' ').title(),
                    description=f"Shipment status updated to {status.replace('_', ' ').title()} by Administrator."
                )
                
                panel_messages.add_admin_message(request, 'success', f"Shipment updated successfully by Admin to {status.replace('_', ' ').title()}.")
        except Exception as e:
            panel_messages.add_admin_message(request, 'error', f"Error updating shipment: {str(e)}")
        
    return redirect(request.META.get('HTTP_REFERER', 'manage_shipments'))

@admin_required
def detail_shipment(request, pk):
    shipment = get_object_or_404(
        Shipment.objects.filter(is_deleted=False).select_related(
            'order_item', 'order_item__order', 'order_item__order__customer',
            'order_item__order__customer__user', 'order_item__order__shipping_address',
            'order_item__product_variant', 'order_item__product_variant__product',
            'order_item__product_variant__size', 'order_item__product_variant__color',
            'vendor'
        ).prefetch_related('history'),
        pk=pk
    )
    return render(request, 'dashboard/shipment_detail.html', {'shipment': shipment})


@admin_required
def manage_payments(request):
    search_query = request.GET.get('q', '')
    status_filter = request.GET.get('status', '')
    sort_by = request.GET.get('sort', 'date_newest')
    date_filter = request.GET.get('date_filter', 'all')
    start_date_str = request.GET.get('start_date', '')
    end_date_str = request.GET.get('end_date', '')
    
    start_date, end_date = get_date_range(date_filter, start_date_str, end_date_str)

    payments = Payment.objects.filter(is_deleted=False).select_related(
        'order', 'order__customer', 'order__customer__user'
    )

    # Date Filtering
    if start_date:
        payments = payments.filter(payment_date__gte=start_date)
    if end_date:
        payments = payments.filter(payment_date__lte=end_date)

    if search_query:
        payments = payments.filter(
            Q(razorpay_payment_id__icontains=search_query) |
            Q(order__pk__icontains=search_query) |
            Q(order__customer__user__first_name__icontains=search_query) |
            Q(order__customer__user__email__icontains=search_query)
        )

    if status_filter:
        payments = payments.filter(status=status_filter)

    if sort_by == 'date_oldest':
        payments = payments.order_by('payment_date')
    else: # Default or date_newest
        payments = payments.order_by('-payment_date')

    payment_fields = [
        ('razorpay_payment_id', 'Transaction ID'),
        ('order.pk', 'Order ID'),
        ('order.customer.user.get_full_name', 'Customer'),
        ('order.customer.user.email', 'Email'),
        ('payment_method', 'Method'),
        ('amount', 'Amount'),
        ('order.admin_earnings', 'Earnings (7%)'),
        ('status', 'Status'),
        ('payment_date', 'Date')
    ]

    if request.GET.get('export') == 'csv':
        return export_to_csv(payments, 'payments', payment_fields)
    elif request.GET.get('export') == 'pdf':
        return export_to_pdf(payments, 'payments', payment_fields)

    status_choices = Payment.STATUS_CHOICES

    context = {
        'payments': payments,
        'search_query': search_query,
        'status_filter': status_filter,
        'current_status': status_filter,
        'current_sort': sort_by,
        'status_choices': status_choices,
        'current_filter': date_filter,
        'start_date': start_date_str,
        'end_date': end_date_str
    }
    if request.GET.get('ajax') == '1':
        return render(request, 'dashboard/partials/payment_table.html', context)

    return render(request, 'dashboard/manage_payments.html', context)

@admin_required
def view_reviews(request):
    search_query = request.GET.get('q', '')
    rating_filter = request.GET.get('rating', '')
    sort = request.GET.get('sort', 'newest')
    
    reviews = Review.objects.filter(is_deleted=False).select_related('product', 'customer__user').prefetch_related('media')
    
    if search_query:
        reviews = reviews.filter(
            Q(product__name__icontains=search_query) |
            Q(customer__user__first_name__icontains=search_query) |
            Q(customer__user__last_name__icontains=search_query)
        )
        
    if rating_filter:
        reviews = reviews.filter(rating=rating_filter)
        
    if sort == 'oldest':
        reviews = reviews.order_by('created_at')
    elif sort == 'rating_high':
        reviews = reviews.order_by('-rating', '-created_at')
    elif sort == 'rating_low':
        reviews = reviews.order_by('rating', '-created_at')
    else:
        reviews = reviews.order_by('-created_at')
    
    review_fields = [
        ('product.name', 'Product'),
        ('customer.user.get_full_name', 'Customer'),
        ('customer.user.email', 'Email'),
        ('rating', 'Rating'),
        ('comment', 'Comment'),
        ('created_at', 'Date')
    ]

    if request.GET.get('export') == 'csv':
        return export_to_csv(reviews, 'reviews', review_fields)
    elif request.GET.get('export') == 'pdf':
        return export_to_pdf(reviews, 'reviews', review_fields)

    context = {
        'reviews': reviews,
        'search_query': search_query,
        'rating_filter': rating_filter,
        'current_sort': sort
    }
    return render(request, 'dashboard/view_reviews.html', context)

@admin_required
def detail_review(request, pk):
    review = get_object_or_404(Review, pk=pk)
    return render(request, 'dashboard/review_detail.html', {'review': review})

@admin_required
def delete_review(request, pk):
    try:
        if request.method == "POST":
            review = get_object_or_404(Review, pk=pk)
            review.is_deleted = True
            review.save()
            messages.success(request, "Review deleted successfully.")
            return redirect('view_reviews')
        return redirect('view_reviews')
    except Exception as e:
        print(f"Error in delete_review: {e}")
        messages.error(request, 'An error occurred.')
        return redirect('view_reviews')

@admin_required
def view_complaints(request):
    search_query = request.GET.get('q', '')
    status_filter = request.GET.get('status', '')
    sort = request.GET.get('sort', 'newest')
    
    complaints = Complaint.objects.filter(is_deleted=False).select_related('customer__user')
    
    if search_query:
        if search_query.startswith('#'):
            ticket_id = search_query[1:]
            if ticket_id.isdigit():
                complaints = complaints.filter(pk=ticket_id)
        else:
            complaints = complaints.filter(
                Q(subject__icontains=search_query) |
                Q(description__icontains=search_query) |
                Q(customer__user__first_name__icontains=search_query) |
                Q(customer__user__last_name__icontains=search_query)
            )
            
    if status_filter:
        complaints = complaints.filter(status=status_filter)
        
    if sort == 'oldest':
        complaints = complaints.order_by('created_at')
    else:
        complaints = complaints.order_by('-created_at')
    
    complaint_fields = [
        ('pk', 'Ticket ID'),
        ('customer.user.get_full_name', 'Customer'),
        ('customer.user.email', 'Email'),
        ('subject', 'Subject'),
        ('description', 'Description'),
        ('status', 'Status'),
        ('created_at', 'Date')
    ]

    if request.GET.get('export') == 'csv':
        return export_to_csv(complaints, 'complaints', complaint_fields)
    elif request.GET.get('export') == 'pdf':
        return export_to_pdf(complaints, 'complaints', complaint_fields)

    # Pagination
    paginator = Paginator(complaints, 10)
    page_number = request.GET.get('page')
    complaints_page = paginator.get_page(page_number)
    
    context = {
        'complaints': complaints_page,
        'search_query': search_query,
        'status_filter': status_filter,
        'current_sort': sort,
        'status_choices': Complaint.STATUS_CHOICES
    }
    return render(request, 'dashboard/view_complaints.html', context)

@admin_required
def admin_update_complaint_status(request, pk):
    complaint = get_object_or_404(Complaint, pk=pk, is_deleted=False)
    
    if request.method == 'POST':
        try:
            new_status = request.POST.get('status')
            if new_status in dict(Complaint.STATUS_CHOICES):
                complaint.status = new_status
                if new_status == 'Resolved':
                    complaint.resolved_at = timezone.now()
                else:
                    complaint.resolved_at = None
                complaint.save()
                
                panel_messages.add_admin_message(request, 'success', f"Complaint #{pk} status updated to {new_status}.")
            else:
                panel_messages.add_admin_message(request, 'error', "Invalid status selected.")
        except Exception as e:
            panel_messages.add_admin_message(request, 'error', f"Error updating complaint: {str(e)}")
            
    return redirect('view_complaints')

@admin_required
def delete_complaint(request, pk):
    try:
        if request.method == "POST":
            complaint = get_object_or_404(Complaint, pk=pk)
            complaint.is_deleted = True
            complaint.save()
            panel_messages.add_admin_message(request, 'success', f"Complaint #{pk} deleted successfully.")
            return redirect('view_complaints')
        return redirect('view_complaints')
    except Exception as e:
        print(f"Error in delete_complaint: {e}")
        panel_messages.add_admin_message(request, 'error', 'An error occurred while deleting the complaint.')
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
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # Important!
            messages.success(request, "Password changed successfully.")
            return redirect('admin_profile')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = PasswordChangeForm(request.user)

    return render(request, 'dashboard/change_password.html', {'form': form})

@admin_required
def manage_requests(request):
    type_filter = request.GET.get('type', '')
    vendor_id = request.GET.get('vendor', '')
    sort = request.GET.get('sort', 'newest')
    
    requests = AttributeRequest.objects.filter(status='Pending').select_related('vendor', 'vendor__user')
    
    if type_filter:
        requests = requests.filter(attribute_type=type_filter)
        
    if vendor_id:
        requests = requests.filter(vendor_id=vendor_id)
        
    if sort == 'oldest':
        requests = requests.order_by('created_at')
    else:
        requests = requests.order_by('-created_at')

    request_fields = [
        ('vendor.shopName', 'Vendor Shop'),
        ('vendor.user.get_full_name', 'Vendor Name'),
        ('attribute_type', 'Type'),
        ('attribute_value', 'Requested Value'),
        ('created_at', 'Date')
    ]

    if request.GET.get('export') == 'csv':
        return export_to_csv(requests, 'attribute_requests', request_fields)
    elif request.GET.get('export') == 'pdf':
        return export_to_pdf(requests, 'attribute_requests', request_fields)

    context = {
        'requests': requests,
        'vendors': Vendor.objects.filter(is_deleted=False),
        'current_type': type_filter,
        'current_vendor': int(vendor_id) if vendor_id and vendor_id.isdigit() else '',
        'current_sort': sort,
        'type_choices': AttributeRequest.REQUEST_TYPES
    }
    return render(request, 'dashboard/manage_requests.html', context)

@admin_required
def approve_request(request, pk):
    req = get_object_or_404(AttributeRequest, pk=pk)
    if req.status == 'Pending':
        try:
            if req.attribute_type == 'Category':
                Category.objects.get_or_create(name=req.attribute_value)
            elif req.attribute_type == 'Size':
                Size.objects.get_or_create(size_label=req.attribute_value)
            elif req.attribute_type == 'Color':
                Color.objects.get_or_create(name=req.attribute_value, defaults={'hex_code': '#000000'})
            
            req.status = 'Approved'
            req.save()
            messages.success(request, f"{req.attribute_type} '{req.attribute_value}' approved and created.")
        except Exception as e:
            messages.error(request, f"Error approving request: {e}")
    return redirect('manage_requests')

@admin_required
def reject_request(request, pk):
    req = get_object_or_404(AttributeRequest, pk=pk)
    if req.status == 'Pending':
        req.status = 'Rejected'
        req.save()
        messages.success(request, "Request rejected.")
    return redirect('manage_requests')

@admin_required
def manage_sizes(request):
    if request.method == 'POST':
        form = SizeForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Size added successfully.")
            return redirect('manage_sizes')
        else:
            messages.error(request, "Error adding size.")
    else:
        form = SizeForm()
    
    q = request.GET.get('q', '')
    sizes = Size.objects.all()
    
    sizes = sizes.order_by('size_label')
    
    if request.GET.get('export') == 'csv':
        fields = [
            ('size_label', 'Size Label')
        ]
        return export_to_csv(sizes, 'sizes', fields)
    elif request.GET.get('export') == 'pdf':
        fields = [
            ('size_label', 'Size Label')
        ]
        return export_to_pdf(sizes, 'sizes', fields)
        
    context = {
        'sizes': sizes,
        'form': form,
        'q': q,
    }

    if request.GET.get('ajax') == '1':
        return render(request, 'dashboard/partials/size_table.html', context) # Need to check if this exists or if I should create it
        
    return render(request, 'dashboard/manage_sizes.html', context)

@admin_required
def delete_size(request, pk):
    size = get_object_or_404(Size, pk=pk)
    try:
        size.delete()
        messages.success(request, "Size deleted successfully.")
    except Exception as e:
        messages.error(request, "Cannot delete this size as it is being used by products.")
    return redirect('manage_sizes')

@admin_required
def manage_colors(request):
    if request.method == 'POST':
        form = ColorForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Color added successfully.")
            return redirect('manage_colors')
        else:
            messages.error(request, "Error adding color.")
    else:
        form = ColorForm()
    
    q = request.GET.get('q', '')
    colors = Color.objects.all()
    
    colors = colors.order_by('name')
    
    if request.GET.get('export') == 'csv':
        fields = [
            ('name', 'Color Name'),
            ('hex_code', 'Hex Code')
        ]
        return export_to_csv(colors, 'colors', fields)
    elif request.GET.get('export') == 'pdf':
        fields = [
            ('name', 'Color Name'),
            ('hex_code', 'Hex Code')
        ]
        return export_to_pdf(colors, 'colors', fields)
        
    context = {
        'colors': colors,
        'form': form,
        'q': q,
    }

    if request.GET.get('ajax') == '1':
        return render(request, 'dashboard/partials/color_table.html', context) # Need to check if this exists or create it
        
    return render(request, 'dashboard/manage_colors.html', context)

@admin_required
def delete_color(request, pk):
    color = get_object_or_404(Color, pk=pk)
    try:
        color.delete()
        messages.success(request, "Color deleted successfully.")
    except Exception as e:
        messages.error(request, "Cannot delete this color as it is being used by products.")
    return redirect('manage_colors')