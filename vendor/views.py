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
from utils import panel_messages

class MockObj:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


# Create your views here.
@vendor_required
def vendor_dashboard(request):
    vendor = request.user.vendor_profile
    
    # Analytics Data
    analytics = MockObj(
        total_sales="₹24,500",
        sales_growth="12.5",
        total_orders="156",
        orders_growth="5.8",
        avg_order_value="₹157",
        aov_growth="1.2",
        products_sold="45",
        products_sold_growth="10.4"
    )

    # Recent Orders (Mock)
    order_items = [
        MockObj(
            pk=1,
            order=MockObj(pk=7829, customer=MockObj(name="John Maker"), order_date=datetime.now() - timedelta(days=2)),
            product_variant=MockObj(product=MockObj(name="Nike Air Max 90")),
            price=4999.00,
            shipment=MockObj(status='delivered')
        ),
         MockObj(
            pk=2,
            order=MockObj(pk=7835, customer=MockObj(name="Sarah Connor"), order_date=datetime.now() - timedelta(days=1)),
            product_variant=MockObj(product=MockObj(name="Puma T-Shirt")),
            price=1299.00,
            shipment=MockObj(status='shipped')
        )
    ]

    context = {
        'analytics': analytics,
        'order_items': order_items,
    }
    return render(request, 'vendor_dashboard.html', context)

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
    # Mock Data for Vendor Orders
    # In a real scenario, this would filter OrderItems by the current vendor
    from .views import MockObj # Ensure MockObj is available or define it if needed (it is defined at top of file)
    
    order_items = [
        MockObj(
            pk=1, # OrderItem ID
            order=MockObj(
                pk=7829, # Order ID
                customer=MockObj(
                    user=MockObj(first_name="John", last_name="Maker", email="j***@example.com"),
                    phone="+91 *********10"
                ),
                order_date=datetime.now() - timedelta(days=2),
                payment=MockObj(status='completed', payment_method='Razorpay', razorpay_order_id='razor_O123'),
                shipping_address=MockObj(
                    address_line1="123, Green Park Avenue",
                    address_line2="Sector 15",
                    city="New Delhi",
                    state="Delhi",
                    postal_code="110016"
                )
            ),
            price=14999.00,
            quantity=1,
            product_variant=MockObj(
                product=MockObj(name="Nike Air Jordan 1 Low"),
                size=MockObj(size_label="UK 9"),
                color=MockObj(name="Chicago Red"),
                image=MockObj(url="/media/photos/products/p1.png")
            ),
            shipment=MockObj(
                pk=101, # Shipment ID
                status='delivered', 
                tracking_number="BD_AJ123456", 
                courier_name="BlueDart",
                expected_delivery=datetime.now() - timedelta(hours=5),
                history=[
                    MockObj(status="Delivered", date=datetime.now() - timedelta(hours=5), description="Handed over to customer."),
                    MockObj(status="In Transit", date=datetime.now() - timedelta(days=1), description="Arrived at local hub."),
                    MockObj(status="Shipped", date=datetime.now() - timedelta(days=2), description="Picked up by BlueDart.")
                ]
            )
        ),
         MockObj(
            pk=2,
            order=MockObj(
                pk=7835,
                customer=MockObj(
                    user=MockObj(first_name="Sarah", last_name="Connor", email="s***@example.com"),
                    phone="+91 *********55"
                ),
                order_date=datetime.now() - timedelta(days=1),
                payment=MockObj(status='pending', payment_method='COD', razorpay_order_id='-'),
                shipping_address=MockObj(
                    address_line1="456, Cyberdyne Systems",
                    address_line2="Industrial Block B",
                    city="Los Angeles",
                    state="California",
                    postal_code="90001"
                )
            ),
            price=24999.00,
            quantity=1,
            product_variant=MockObj(
                product=MockObj(name="Adidas Yeezy Boost 350"),
                size=MockObj(size_label="UK 8"),
                color=MockObj(name="Onyx"),
                image=None
            ),
            shipment=MockObj(
                pk=102,
                status='in_transit', 
                tracking_number="DL_YZ987654", 
                courier_name="Delhivery",
                expected_delivery=datetime.now() + timedelta(days=2),
                history=[
                    MockObj(status="In Transit", date=datetime.now() - timedelta(hours=2), description="In transit to destination."),
                    MockObj(status="Shipped", date=datetime.now() - timedelta(days=1), description="Dispatched from hub.")
                ]
            )
        ),
        MockObj(
            pk=3,
            order=MockObj(
                pk=7840,
                customer=MockObj(
                    user=MockObj(first_name="Mike", last_name="Ross", email="m***@pearson-specter.com"),
                    phone="+91 *********44"
                ),
                order_date=datetime.now(),
                payment=MockObj(status='completed', payment_method='Credit Card', razorpay_order_id='razor_O440'),
                shipping_address=MockObj(
                    address_line1="789, Wall Street",
                    address_line2="Floor 42",
                    city="Manhattan",
                    state="New York",
                    postal_code="10005"
                )
            ),
            price=8999.00,
            quantity=1,
            product_variant=MockObj(
                product=MockObj(name="Nike Pegasus 40"),
                size=MockObj(size_label="UK 10"),
                color=MockObj(name="Volt Green"),
                image=None
            ),
            shipment=MockObj(
                pk=103,
                status='pending', 
                tracking_number=None, 
                courier_name=None,
                expected_delivery=datetime.now() + timedelta(days=4),
                history=[
                    MockObj(status="Pending", date=datetime.now(), description="Awaiting pickup.")
                ]
            )
        )
    ]
    return render(request, 'vendor_orders.html', {'order_items': order_items})

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

                    panel_messages.add_vendor_message(request, 'success', "Product added successfully.")
                    return redirect('vendor_products')
            except Exception as e:
                panel_messages.add_vendor_message(request, 'error', f"Error adding product: {e}")
        else:
             panel_messages.add_vendor_message(request, 'error', f"Form error: {form.errors}")
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
        panel_messages.add_vendor_message(request, 'error', "Product not found or unauthorized.")
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
                                
                    panel_messages.add_vendor_message(request, 'success', "Product updated successfully.")
                    return redirect('vendor_products')
            except Exception as e:
                import traceback
                traceback.print_exc()
                panel_messages.add_vendor_message(request, 'error', f"Error updating product: {e}")
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
        panel_messages.add_vendor_message(request, 'success', "Product soft-deleted successfully.")
    except Product.DoesNotExist:
        panel_messages.add_vendor_message(request, 'error', "Product not found or unauthorized.")
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
def vendor_product_detail(request, pk):
    product = get_object_or_404(Product, pk=pk, vendor=request.user.vendor_profile, is_deleted=False)
    variants = product.productvariant_set.filter(is_deleted=False).select_related('size', 'color')
    return render(request, 'vendor_product_detail.html', {'product': product, 'variants': variants})

@vendor_required
def vendor_category_detail(request, pk):
    category = get_object_or_404(Category, pk=pk, is_deleted=False)
    return render(request, 'vendor_category_detail.html', {'category': category})

@vendor_required
def vendor_review_detail(request, pk):
    try:
        review = Review.objects.get(pk=pk, product__vendor=request.user.vendor_profile, is_deleted=False)
    except Review.DoesNotExist:
        # Rich Mock Data Fallback
        review = MockObj(
            pk=pk,
            customer=MockObj(user=MockObj(first_name="Customer", last_name="#"+str(pk))),
            rating=5,
            comment="Absolutely love these shoes! The comfort level is insane and they look even better in person.",
            created_at=datetime.now() - timedelta(days=2),
            product=MockObj(name="Nike Air Max 90", product_image=None, category=MockObj(name="Sneakers")),
            media=MockObj(all=lambda: [])
        )
    return render(request, 'vendor_review_detail.html', {'review': review})

@vendor_required
def vendor_shipment_detail(request, pk):
    try:
        shipment = Shipment.objects.get(pk=pk)
    except Shipment.DoesNotExist:
        # Rich Mock Data Fallback
        shipment = MockObj(
            pk=pk,
            status="in_transit",
            courier_name="BlueDart",
            tracking_number="BD_8822991100",
            shipped_at=datetime.now() - timedelta(days=1),
            expected_delivery=datetime.now() + timedelta(days=3),
            history=[
                MockObj(status="In Transit", date=datetime.now() - timedelta(hours=5), description="Shipment is out for delivery."),
                MockObj(status="Shipped", date=datetime.now() - timedelta(days=1), description="Shipment left the vendor facility."),
                MockObj(status="Pending", date=datetime.now() - timedelta(days=1, hours=4), description="Shipment order created.")
            ],
            order_item=MockObj(
                order=MockObj(
                    pk=7829, 
                    customer=MockObj(
                        user=MockObj(first_name="John", last_name="Maker", email="j***@example.com"),
                        phone="+91 *********10"
                    ),
                    shipping_address=MockObj(
                        address_line1="123, Green Park Avenue",
                        address_line2="Sector 15",
                        city="New Delhi",
                        state="Delhi",
                        postal_code="110016"
                    )
                ),
                product_variant=MockObj(
                    product=MockObj(name="Nike Air Max 90"),
                    size=MockObj(size_label="UK 9"),
                    color=MockObj(name="White/Red"),
                    image=MockObj(url="/media/photos/products/p1.png")
                ),
                quantity=1
            )
        )
    return render(request, 'vendor_shipment_detail.html', {'shipment': shipment})

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
    if request.method == 'POST':
        status = request.POST.get('status')
        courier = request.POST.get('courier_name')
        tracking = request.POST.get('tracking_number')

        if status == 'in_transit' and (not courier or not tracking):
            panel_messages.add_vendor_message(request, 'error', "Courier and Tracking Number are required for In Transit status.")
        else:
            # Here we would update the actual model
            # Shipment.objects.filter(pk=pk).update(status=status, ...)
            panel_messages.add_vendor_message(request, 'success', f"Shipment #{pk} updated successfully to {status.replace('_', ' ').title()}.")
            
    return redirect(request.META.get('HTTP_REFERER', 'vendor_orders'))

@vendor_required
def create_shipment(request, order_item_id):
    if request.method == 'POST':
        panel_messages.add_vendor_message(request, 'success', 'Shipment created successfully!')
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
        panel_messages.add_vendor_message(request, 'info', 'Profile update feature coming soon.')
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
            panel_messages.add_vendor_message(request, 'error', "Incorrect current password.")
        elif new_password != confirm_password:
            panel_messages.add_vendor_message(request, 'error', "New passwords do not match.")
        else:
            request.user.set_password(new_password)
            request.user.save()
            update_session_auth_hash(request, request.user)
            panel_messages.add_vendor_message(request, 'success', "Password changed successfully.")
            return redirect('vendor_profile')
    
    return render(request, 'vendor_change_password.html')
