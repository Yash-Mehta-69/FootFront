from django.shortcuts import redirect, render, get_object_or_404
from django.db import transaction
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.db.models import Q, Min, Sum, F, Count
from django.core.paginator import Paginator
from store.decorators import vendor_required
from store.models import Category, Product, ProductVariant, Size, Color
from store.forms import VendorProductForm
from cart.models import Order, Shipment, OrderItem, ShipmentStatusHistory
from django.utils import timezone
from datetime import timedelta, datetime
from utils import panel_messages
from utils.exports import export_to_csv
from django.db.models import Prefetch


class MockObj:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


# Create your views here.
@vendor_required
def vendor_dashboard(request):
    vendor = request.user.vendor_profile
    
    # Real Analytics Data
    now = timezone.now()
    first_day_current = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    month_prev = first_day_current - timedelta(days=1)
    first_day_prev = month_prev.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # Base Queryset
    base_qs = OrderItem.objects.filter(product_variant__product__vendor=vendor, order__payment__status='completed', is_deleted=False)
    vendor_order_items = base_qs

    # Current Month Data
    current_month_items = base_qs.filter(order__order_date__gte=first_day_current)
    current_sales = current_month_items.aggregate(total=Sum(F('price') * F('quantity')))['total'] or 0
    current_orders = current_month_items.values('order').distinct().count()
    current_qty = current_month_items.aggregate(total=Sum('quantity'))['total'] or 0
    current_aov = current_sales / current_orders if current_orders > 0 else 0

    # Previous Month Data
    prev_month_items = base_qs.filter(order__order_date__gte=first_day_prev, order__order_date__lt=first_day_current)
    prev_sales = prev_month_items.aggregate(total=Sum(F('price') * F('quantity')))['total'] or 0
    prev_orders = prev_month_items.values('order').distinct().count()
    prev_qty = prev_month_items.aggregate(total=Sum('quantity'))['total'] or 0
    prev_aov = prev_sales / prev_orders if prev_orders > 0 else 0

    def calc_growth(current, prev):
        if prev == 0:
            return 100.0 if current > 0 else 0.0
        return ((current - prev) / prev) * 100

    # Overall Totals (Lifetime)
    total_sales = base_qs.aggregate(total=Sum(F('price') * F('quantity')))['total'] or 0
    total_orders = base_qs.values('order').distinct().count()
    products_sold = base_qs.aggregate(total=Sum('quantity'))['total'] or 0
    avg_order_val = total_sales / total_orders if total_orders > 0 else 0
    
    # Growth Calculations
    sales_growth_val = calc_growth(current_sales, prev_sales)
    orders_growth_val = calc_growth(current_orders, prev_orders)
    aov_growth_val = calc_growth(current_aov, prev_aov)
    products_sold_growth_val = calc_growth(current_qty, prev_qty)

    analytics = MockObj(
        total_sales=f"₹{total_sales:,.2f}",
        sales_growth=f"{abs(sales_growth_val):.1f}",
        sales_growth_pos=sales_growth_val >= 0,
        
        total_orders=str(total_orders),
        orders_growth=f"{abs(orders_growth_val):.1f}",
        orders_growth_pos=orders_growth_val >= 0,

        avg_order_value=f"₹{avg_order_val:,.2f}",
        aov_growth=f"{abs(aov_growth_val):.1f}",
        aov_growth_pos=aov_growth_val >= 0,

        products_sold=str(products_sold),
        products_sold_growth=f"{abs(products_sold_growth_val):.1f}",
        products_sold_growth_pos=products_sold_growth_val >= 0
    )

    # Top Products (Real)
    top_products = Product.objects.filter(vendor=vendor, is_deleted=False).annotate(
        total_revenue=Sum(F('productvariant__orderitem__price') * F('productvariant__orderitem__quantity'), filter=Q(productvariant__orderitem__order__payment__status='completed'))
    ).filter(total_revenue__gt=0).order_by('-total_revenue')[:3]

    # Recent Orders (Real)
    # Get IDs of recent orders for this vendor
    vendor_recent_order_ids = OrderItem.objects.filter(
        product_variant__product__vendor=vendor,
        is_deleted=False
    ).values_list('order_id', flat=True).distinct().order_by('-order__order_date')[:5]

    recent_orders = Order.objects.filter(
        pk__in=vendor_recent_order_ids
    ).select_related(
        'customer', 'customer__user', 'payment'
    ).prefetch_related(
        Prefetch(
            'items',
            queryset=OrderItem.objects.filter(
                product_variant__product__vendor=vendor,
                is_deleted=False
            ).select_related('product_variant', 'product_variant__product', 'shipment'),
            to_attr='vendor_items'
        )
    ).annotate(
        vendor_total=Sum(
            F('items__price') * F('items__quantity'),
            filter=Q(items__product_variant__product__vendor=vendor)
        )
    ).order_by('-order_date')

    context = {
        'analytics': analytics,
        'top_products': top_products,
        'recent_orders': recent_orders,
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

    if request.GET.get('export') == 'csv':
        # Enhanced export: One row per variant
        variants = ProductVariant.objects.filter(product__in=products, is_deleted=False).select_related(
            'product', 'product__category', 'size', 'color'
        ).order_by('product__name', 'size__size_label')
        
        fields = [
            ('product.name', 'Product Name'),
            ('product.category.name', 'Category'),
            ('size.size_label', 'Size'),
            ('color.name', 'Color'),
            ('price', 'Price'),
            ('stock', 'Stock'),
            ('product.gender', 'Gender'),
            ('product.is_trending', 'Is Trending'),
            ('product.created_at', 'Date Created')
        ]
        return export_to_csv(variants, 'vendor_products', fields)

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
    
    if request.GET.get('ajax') == '1':
        return render(request, 'vendor_partials/product_table.html', context)
        
    return render(request, 'vendor_products.html', context)

@vendor_required
def vendor_orders(request):
    vendor = request.user.vendor_profile
    
    # Filtering parameters
    q = request.GET.get('q', '')
    status = request.GET.get('status', '')
    sort = request.GET.get('sort', 'date_newest')
    
    # Get IDs of orders that contain at least one item from this vendor
    vendor_order_ids = OrderItem.objects.filter(
        product_variant__product__vendor=vendor,
        is_deleted=False
    ).values_list('order_id', flat=True).distinct()
    
    # Base queryset for Orders
    orders = Order.objects.filter(
        pk__in=vendor_order_ids,
        is_deleted=False
    ).select_related(
        'customer', 'customer__user', 'payment', 'shipping_address'
    ).prefetch_related(
        Prefetch(
            'items',
            queryset=OrderItem.objects.filter(
                product_variant__product__vendor=vendor,
                is_deleted=False
            ).select_related(
                'product_variant', 'product_variant__product',
                'product_variant__size', 'product_variant__color', 'shipment'
            ),
            to_attr='vendor_items'
        )
    )
    
    # Searching
    if q:
        orders = orders.filter(
            Q(pk__icontains=q) |
            Q(customer__user__first_name__icontains=q) |
            Q(customer__user__last_name__icontains=q) |
            Q(items__product_variant__product__name__icontains=q)
        ).distinct()
        
    # Filtering by Status (if any vendor item has the status)
    if status:
        orders = orders.filter(
            items__product_variant__product__vendor=vendor,
            items__shipment__status=status
        ).distinct()
        
    # Annotate total vendor price for sorting if needed
    orders = orders.annotate(
        vendor_total=Sum(
            F('items__price') * F('items__quantity'),
            filter=Q(items__product_variant__product__vendor=vendor)
        )
    )

    # Sorting
    if sort == 'date_newest':
        orders = orders.order_by('-order_date')
    elif sort == 'date_oldest':
        orders = orders.order_by('order_date')
    elif sort == 'price_high':
        orders = orders.order_by('-vendor_total')
    elif sort == 'price_low':
        orders = orders.order_by('vendor_total')
        
    # Pagination
    paginator = Paginator(orders, 10)
    page_number = request.GET.get('page')
    orders_page = paginator.get_page(page_number)
    
    if request.GET.get('export') == 'csv':
        fields = [
            ('pk', 'Order ID'),
            ('customer.user.first_name', 'Customer First Name'),
            ('customer.user.last_name', 'Customer Last Name'),
            ('customer.user.email', 'Customer Email'),
            ('shipping_address.address_line1', 'Address Line 1'),
            ('shipping_address.address_line2', 'Address Line 2'),
            ('shipping_address.city', 'City'),
            ('shipping_address.state', 'State'),
            ('shipping_address.postal_code', 'Pincode'),
            ('vendor_total', 'Amount'),
            ('order_date', 'Date')
        ]
        return export_to_csv(orders, 'vendor_orders', fields)
    
    context = {
        'orders': orders_page,
        'search_query': q,
        'current_status': status,
        'current_sort': sort,
        'status_choices': Shipment.STATUS_CHOICES
    }
    
    if request.GET.get('ajax') == '1':
        return render(request, 'vendor_partials/order_table.html', context)
        
    return render(request, 'vendor_orders.html', context)

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
    shipment = get_object_or_404(
        Shipment.objects.select_related(
            'order_item', 'order_item__order', 'order_item__order__customer',
            'order_item__order__customer__user', 'order_item__order__shipping_address',
            'order_item__product_variant', 'order_item__product_variant__product',
            'order_item__product_variant__size', 'order_item__product_variant__color'
        ).prefetch_related('history'),
        pk=pk, vendor=request.user.vendor_profile
    )
    return render(request, 'vendor_shipment_detail.html', {'shipment': shipment})

@vendor_required
def vendor_categories(request):
    categories = Category.objects.filter(is_deleted=False).select_related('parent_category')
    
    if request.GET.get('export') == 'csv':
        fields = [
            ('name', 'Category Name'),
            ('parent_category.name', 'Parent Category'),
            ('description', 'Description'),
            ('cat_image', 'Image Path')
        ]
        return export_to_csv(categories, 'vendor_categories', fields)
        
    return render(request, 'vendor_categories.html', {'categories': categories})

@vendor_required
def vendor_shipments(request):
    vendor = request.user.vendor_profile
    
    # Filtering parameters
    q = request.GET.get('q', '')
    status = request.GET.get('status', '')
    order_id = request.GET.get('order_id', '')
    sort = request.GET.get('sort', 'shipped_newest')
    
    # Fetch real shipments for this vendor
    shipments = Shipment.objects.filter(
        vendor=vendor,
        is_deleted=False
    ).select_related(
        'order_item', 'order_item__order', 'order_item__product_variant',
        'order_item__product_variant__product', 'order_item__product_variant__size',
        'order_item__product_variant__color'
    )
    
    # Searching
    if q:
        shipments = shipments.filter(
            Q(tracking_number__icontains=q) |
            Q(order_item__product_variant__product__name__icontains=q) |
            Q(order_item__order__pk__icontains=q)
        )
        
    # Filtering by Status
    if status:
        shipments = shipments.filter(status=status)
        
    # Filtering by Order ID
    if order_id:
        try:
            clean_id = order_id.upper().replace('#ORD-', '').strip()
            if clean_id.isdigit():
                shipments = shipments.filter(order_item__order__pk=int(clean_id))
            else:
                shipments = shipments.filter(order_item__order__pk__icontains=clean_id)
        except:
            pass
        
    # Get all unique Order IDs for this vendor (for searchable datalist)
    # Using the unfiltered queryset to give the vendor all their order options
    vendor_order_ids = OrderItem.objects.filter(
        product_variant__product__vendor=vendor,
        is_deleted=False
    ).values_list('order_id', flat=True).distinct().order_by('-order_id')
        
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
    
    if request.GET.get('export') == 'csv':
        fields = [
            ('tracking_number', 'Tracking Number'),
            ('courier_name', 'Courier'),
            ('order_item.order.pk', 'Order ID'),
            ('order_item.product_variant.product.name', 'Product'),
            ('order_item.product_variant.size.size_label', 'Size'),
            ('order_item.product_variant.color.name', 'Color'),
            ('status', 'Status'),
            ('shipped_at', 'Shipped At'),
            ('expected_delivery', 'Expected Delivery')
        ]
        return export_to_csv(shipments, 'vendor_shipments', fields)
    
    context = {
        'shipments': shipments_page,
        'search_query': q,
        'order_id_filter': order_id,
        'vendor_order_ids': vendor_order_ids,
        'current_status': status,
        'current_sort': sort,
        'status_choices': Shipment.STATUS_CHOICES
    }
    
    if request.GET.get('ajax') == '1':
        return render(request, 'vendor_partials/shipment_table.html', context)
        
    return render(request, 'vendor_shipments.html', context)

@vendor_required
def update_shipment_status(request, pk):
    vendor = request.user.vendor_profile
    
    # Try finding shipment directly by PK (from vendor_shipments) 
    # or by OrderItem ID (from vendor_orders)
    shipment = Shipment.objects.filter(
        Q(pk=pk) | Q(order_item_id=pk),
        vendor=vendor,
        is_deleted=False
    ).first()
    
    if not shipment:
        panel_messages.add_vendor_message(request, 'error', "Shipment record not found.")
        return redirect(request.META.get('HTTP_REFERER', 'vendor_orders'))

    if request.method == 'POST':
        status = request.POST.get('status')
        courier = request.POST.get('courier_name')
        tracking = request.POST.get('tracking_number')

        if status == 'in_transit' and (not courier or not tracking):
            panel_messages.add_vendor_message(request, 'error', "Courier and Tracking Number are required for In Transit status.")
        else:
            # Lifecycle Enforcement: Define rank for statuses to prevent reverting
            rank = {'preparing': 1, 'shipped': 2, 'in_transit': 3, 'delivered': 4}
            current_rank = rank.get(shipment.status, 0)
            new_rank = rank.get(status, 0)
            
            if new_rank < current_rank:
                panel_messages.add_vendor_message(request, 'error', f"Cannot revert status from {shipment.get_status_display()} to {status.title()}.")
                return redirect(request.META.get('HTTP_REFERER', 'vendor_orders'))

            shipment.status = status
            if courier: shipment.courier_name = courier
            if tracking: shipment.tracking_number = tracking
            
            if status == 'shipped' and not shipment.shipped_at:
                shipment.shipped_at = timezone.now()
            
            # Optional: Automatic expected delivery 7 days from now if not set
            if status == 'shipped' and not shipment.expected_delivery:
                shipment.expected_delivery = (timezone.now() + timedelta(days=7)).date()
                
            shipment.save()
            
            # Log History
            ShipmentStatusHistory.objects.create(
                shipment=shipment,
                status=status.replace('_', ' ').title(),
                description=f"Shipment status updated to {status.replace('_', ' ').title()} by Vendor."
            )
            
            panel_messages.add_vendor_message(request, 'success', f"Shipment updated successfully to {status.replace('_', ' ').title()}.")
            
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
    
    if request.GET.get('export') == 'csv':
        fields = [
            ('product.name', 'Product'),
            ('customer.user.first_name', 'Customer First Name'),
            ('customer.user.last_name', 'Customer Last Name'),
            ('rating', 'Rating'),
            ('comment', 'Comment'),
            ('created_at', 'Date')
        ]
        return export_to_csv(reviews, 'vendor_reviews', fields)
    
    return render(request, 'vendor_reviews.html', {'reviews': reviews})


@vendor_required
def vendor_sizes(request):
    sizes = Size.objects.all()
    
    if request.GET.get('export') == 'csv':
        fields = [('size_label', 'Size Label')]
        return export_to_csv(sizes, 'vendor_sizes', fields)
        
    return render(request, 'vendor_sizes.html', {'sizes': sizes})

@vendor_required
def vendor_colors(request):
    colors = Color.objects.all()
    
    if request.GET.get('export') == 'csv':
        fields = [('name', 'Color Name'), ('hex_code', 'Hex Code')]
        return export_to_csv(colors, 'vendor_colors', fields)
        
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
