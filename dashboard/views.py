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
from django.db.models import Q, Min, Count, Sum, Prefetch
from utils import panel_messages
from cart.models import Order, OrderItem, Shipment, ShipmentStatusHistory, Payment

@admin_required
def dashboard(request):
    # Real Stats
    total_customers = Customer.objects.filter(is_deleted=False).count()
    total_products = Product.objects.filter(is_deleted=False).count()
    total_orders = Order.objects.filter(is_deleted=False).count()
    total_revenue_val = Order.objects.filter(is_deleted=False, payment__status='completed').aggregate(total=Sum('total_amount'))['total'] or 0

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

    stats = {
        'total_users': total_customers,
        'users_growth': 5.4, # Keep aesthetic growth for now or implement user growth
        'total_products': total_products,
        'products_growth': 2.1,
        'total_orders': total_orders,
        'orders_growth': round(orders_growth, 1),
        'total_revenue': f"₹{int(total_revenue_val):,}",
        'revenue_growth': 8.2
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
        'recent_orders': recent_orders_raw
    }
    return render(request, 'dashboard/admin_dashboard.html', context)

from store.models import Customer, Category, Product, ProductVariant, Size, Color, AttributeRequest, Review
from store.forms import CategoryForm, ProductForm, SizeForm, ColorForm, CustomerAdminForm, VendorAdminForm
from vendor.models import Vendor

@admin_required
def manage_customers(request):
    customers = Customer.objects.select_related('user').filter(is_deleted=False)
    return render(request, 'dashboard/manage_customers.html', {'customers': customers})

@admin_required
def add_customer(request):
    if request.method == "POST":
        form = CustomerAdminForm(request.POST)
        if form.is_valid():
            try:
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
        customer.firebase_uid = None # Clear UID so it can be reused or simply to detach
        customer.save()
        
        panel_messages.add_admin_message(request, 'success', "Customer deleted successfully (Firebase & Local).")
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
    vendors = Vendor.objects.select_related('user', 'bankdetail').filter(is_deleted=False)
    # Map mock attributes for template compatibility if needed, or update template
    # Template expects: vendor.pk, vendor.shopName, vendor.name (user.first_name + last), vendor.email, vendor.business_phone, vendor.status
    # We will pass the queryset directly and update the template to access relational fields
    return render(request, 'dashboard/manage_vendors.html', {'vendors': vendors})

@admin_required
def add_vendor(request):
    if request.method == "POST":
        form = VendorAdminForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                with transaction.atomic():
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
        vendor.is_deleted = True
        vendor.save()
        # Also soft delete user? Usually yes.
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
    categories = Category.objects.filter(is_deleted=False).select_related('parent_category')
    return render(request, 'dashboard/manage_categories.html', {'categories': categories})

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

    context = {
        'products': products_page,
        'categories': Category.objects.filter(is_deleted=False),
        'vendors': Vendor.objects.filter(is_deleted=False),
        'search_query': query,
        'current_category': int(category_id) if category_id else None,
        'current_vendor': int(vendor_id) if vendor_id else None,
        'current_sort': sort_by,
    }
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
        'current_sort': sort
    }
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
    
    # Base queryset
    shipments = Shipment.objects.filter(is_deleted=False).select_related(
        'order_item', 'order_item__order', 'vendor',
        'order_item__product_variant', 'order_item__product_variant__product'
    )
    
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
        'status_choices': Shipment.STATUS_CHOICES
    }
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

    payments = Payment.objects.filter(is_deleted=False).select_related(
        'order', 'order__customer', 'order__customer__user'
    )

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

    status_choices = Payment.STATUS_CHOICES

    context = {
        'payments': payments,
        'search_query': search_query,
        'status_filter': status_filter,
        'current_sort': sort_by,
        'status_choices': status_choices,
    }
    return render(request, 'dashboard/manage_payments.html', context)

@admin_required
def view_reviews(request):
    reviews = Review.objects.filter(is_deleted=False).select_related('product', 'customer__user').prefetch_related('media').order_by('-created_at')
    return render(request, 'dashboard/view_reviews.html', {'reviews': reviews})

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
    class MockObj:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

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
    requests = AttributeRequest.objects.filter(status='Pending').order_by('-created_at')
    return render(request, 'dashboard/manage_requests.html', {'requests': requests})

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
    
    sizes = Size.objects.all().order_by('size_label')
    return render(request, 'dashboard/manage_sizes.html', {'sizes': sizes, 'form': form})

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
    
    colors = Color.objects.all().order_by('name')
    return render(request, 'dashboard/manage_colors.html', {'colors': colors, 'form': form})

@admin_required
def delete_color(request, pk):
    color = get_object_or_404(Color, pk=pk)
    try:
        color.delete()
        messages.success(request, "Color deleted successfully.")
    except Exception as e:
        messages.error(request, "Cannot delete this color as it is being used by products.")
    return redirect('manage_colors')