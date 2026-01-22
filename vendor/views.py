from django.shortcuts import redirect, render, get_object_or_404
from django.db import transaction
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.db.models import Q, Min
from django.core.paginator import Paginator
from store.decorators import vendor_required
from store.models import Category, Product, ProductVariant, Size, Color
from store.forms import VendorProductForm
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
    from django.db.models import Prefetch
    
    # Prefetch only active variants
    active_variants_prefetch = Prefetch(
        'productvariant_set',
        queryset=ProductVariant.objects.filter(is_deleted=False),
        to_attr='active_variants'
    )
    
    products = Product.objects.filter(vendor=request.user.vendor_profile, is_deleted=False).select_related('category').prefetch_related(active_variants_prefetch)
    
    # Filter by Category
    category_id = request.GET.get('category')
    if category_id:
        products = products.filter(category_id=category_id)

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
    else: # Default: Newest
        products = products.order_by('-created_at')

    # Pagination
    paginator = Paginator(products, 10)
    page_number = request.GET.get('page')
    products_page = paginator.get_page(page_number)

    context = {
        'products': products_page,
        'categories': Category.objects.filter(is_deleted=False),
        'search_query': query,
        'current_category': int(category_id) if category_id else None,
        'current_sort': sort_by,
    }
    return render(request, 'vendor_products.html', context)

@vendor_required
def vendor_orders(request):
    return redirect('vendor_shipments') # Orders are now managed via Shipments

@vendor_required
def add_product(request):
    if request.method == "POST":
        form = VendorProductForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                with transaction.atomic():
                    product = form.save(commit=False)
                    product.vendor = request.user.vendor_profile
                    product.save()
                    
                    sizes = request.POST.getlist('variant_size[]')
                    colors = request.POST.getlist('variant_color[]')
                    prices = request.POST.getlist('variant_price[]')
                    stocks = request.POST.getlist('variant_stock[]')

                    variant_count = 0
                    for i in range(len(sizes)):
                        if sizes[i] and colors[i] and prices[i] and stocks[i]:
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

                    messages.success(request, "Product added successfully.")
                    return redirect('vendor_products')
            except Exception as e:
                messages.error(request, f"Error adding product: {e}")
        else:
             messages.error(request, f"Form error: {form.errors}")
    else:
        form = VendorProductForm()

    context = {
        'action': 'Add',
        'form': form,
        'categories': Category.objects.filter(is_deleted=False),
        'sizes': Size.objects.all(),
        'colors': Color.objects.all(),
    }
    return render(request, 'vendor_add_product.html', context)

@vendor_required
def edit_product(request, pk):
    try:
        product = Product.objects.get(pk=pk, vendor=request.user.vendor_profile)
    except Product.DoesNotExist:
        messages.error(request, "Product not found or unauthorized.")
        return redirect('vendor_products')

    if request.method == "POST":
        form = VendorProductForm(request.POST, request.FILES, instance=product)
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
                        if sizes[i] and colors[i] and prices[i] and stocks[i]: # Basic validation
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
                                
                    messages.success(request, "Product updated successfully.")
                    return redirect('vendor_products')
            except Exception as e:
                import traceback
                traceback.print_exc()
                messages.error(request, f"Error updating product: {e}")
    else:
        form = VendorProductForm(instance=product)
        
    existing_variants = product.productvariant_set.filter(is_deleted=False)

    context = {
        'action': 'Edit',
        'form': form,
        'product': product,
        'variants': existing_variants,
        'categories': Category.objects.filter(is_deleted=False),
        'sizes': Size.objects.all(),
        'colors': Color.objects.all(),
    }
    return render(request, 'vendor_edit_product.html', context)

@vendor_required
def delete_product(request, pk):
    try:
        product = Product.objects.get(pk=pk, vendor=request.user.vendor_profile)
        product.is_deleted = True
        product.save()
        messages.success(request, "Product soft-deleted successfully.")
    except Product.DoesNotExist:
        messages.error(request, "Product not found or unauthorized.")
    return redirect('vendor_products')

from django.http import JsonResponse
from store.models import AttributeRequest

@vendor_required
def request_attribute(request):
    if request.method == 'POST':
        import json
        data = json.loads(request.body)
        attr_type = data.get('type') # 'Category', 'Size', 'Color'
        attr_value = data.get('value')
        
        if attr_type and attr_value:
            # Check for duplicates (existing request or existing item)
            # For MVP, just creating request logic
            AttributeRequest.objects.create(
                vendor=request.user.vendor_profile,
                attribute_type=attr_type,
                attribute_value=attr_value
            )
            return JsonResponse({'success': True, 'message': 'Request submitted successfully.'})
        return JsonResponse({'success': False, 'message': 'Invalid data.'})
    return JsonResponse({'success': False, 'message': 'Invalid method.'})

@vendor_required
def product_detail(request):
    return render(request, 'vendor_product_detail.html')

@vendor_required
def vendor_categories(request):
    categories = Category.objects.filter(is_deleted=False).select_related('parent_category')
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

from store.models import Review

@vendor_required
def vendor_reviews(request):
    # Fetch Reviews for Products belonging to this Vendor
    reviews = Review.objects.filter(
        product__vendor=request.user.vendor_profile,
        is_deleted=False
    ).order_by('-created_at')
    
    return render(request, 'vendor_reviews.html', {'reviews': reviews})


@vendor_required
def vendor_sizes(request):
    sizes = Size.objects.all()
    return render(request, 'vendor_sizes.html', {'sizes': sizes})

@vendor_required
def vendor_colors(request):
    colors = Color.objects.all()
    return render(request, 'vendor_colors.html', {'colors': colors})

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
