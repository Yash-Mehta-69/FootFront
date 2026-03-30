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
from django.utils.html import strip_tags
from datetime import timedelta, datetime
from utils.filters import get_date_range
from utils import panel_messages
from utils.exports import export_to_csv, export_to_pdf
from django.db.models import Prefetch
from django.http import JsonResponse
from utils.reports import REPORT_CONFIG


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
    
    # Current Month Data
    current_month_items = base_qs.filter(order__order_date__gte=first_day_current)
    current_sales = current_month_items.aggregate(total=Sum(F('price') * F('quantity')))['total'] or 0
    current_orders = current_month_items.values('order').distinct().count()
    current_qty = current_month_items.aggregate(total=Sum('quantity'))['total'] or 0
    
    # Previous Month Data
    prev_month_items = base_qs.filter(order__order_date__gte=first_day_prev, order__order_date__lt=first_day_current)
    prev_sales = prev_month_items.aggregate(total=Sum(F('price') * F('quantity')))['total'] or 0
    prev_orders = prev_month_items.values('order').distinct().count()
    prev_qty = prev_month_items.aggregate(total=Sum('quantity'))['total'] or 0

    # Calculate current and previous periods for growth
    current_aov = current_sales / current_orders if current_orders > 0 else 0
    prev_aov = prev_sales / prev_orders if prev_orders > 0 else 0

    def calc_growth(current, prev):
        if prev == 0:
            return 100.0 if current > 0 else 0.0
        return ((current - prev) / prev) * 100

    # Growth Calculations
    sales_growth = calc_growth(current_sales, prev_sales)
    orders_growth = calc_growth(current_orders, prev_orders)
    qty_growth = calc_growth(current_qty, prev_qty)
    aov_growth = calc_growth(current_aov, prev_aov)

    # Lifetime Totals
    total_sales = base_qs.aggregate(total=Sum(F('price') * F('quantity')))['total'] or 0
    total_orders = base_qs.values('order').distinct().count()
    products_sold = base_qs.aggregate(total=Sum('quantity'))['total'] or 0
    avg_order_val = total_sales / total_orders if total_orders > 0 else 0
    
    analytics = MockObj(
        total_sales=f"₹{total_sales:,.2f}",
        sales_growth=f"{sales_growth:+.1f}",
        sales_growth_pos=sales_growth >= 0,
        
        total_orders=str(total_orders),
        orders_growth=f"{orders_growth:+.1f}",
        orders_growth_pos=orders_growth >= 0,

        avg_order_value=f"₹{avg_order_val:,.2f}",
        aov_growth=f"{aov_growth:+.1f}",
        aov_growth_pos=aov_growth >= 0,

        products_sold=str(products_sold),
        products_sold_growth=f"{qty_growth:+.1f}",
        products_sold_growth_pos=qty_growth >= 0,
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

    # Graph Data: Weekly (Last 7 Days)
    weekly_labels = []
    weekly_data = []
    for i in range(6, -1, -1):
        day = now - timedelta(days=i)
        weekly_labels.append(day.strftime('%a'))
        day_revenue = base_qs.filter(
            order__order_date__date=day.date()
        ).aggregate(total=Sum(F('price') * F('quantity')))['total'] or 0
        weekly_data.append(float(day_revenue))

    # Graph Data: Yearly (current year)
    yearly_labels = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    yearly_data = []
    for month in range(1, 13):
        month_revenue = base_qs.filter(
            order__order_date__year=now.year,
            order__order_date__month=month
        ).aggregate(total=Sum(F('price') * F('quantity')))['total'] or 0
        yearly_data.append(float(month_revenue))

    context = {
        'analytics': analytics,
        'top_products': top_products,
        'recent_orders': recent_orders,
        'graph_data': {
            'weekly': {'labels': weekly_labels, 'data': weekly_data},
            'yearly': {'labels': yearly_labels, 'data': yearly_data}
        }
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
    elif request.GET.get('export') == 'pdf':
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
        return export_to_pdf(variants, 'vendor_products', fields)

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
    date_filter = request.GET.get('date_filter', 'all')
    start_date_str = request.GET.get('start_date', '')
    end_date_str = request.GET.get('end_date', '')
    
    start_date, end_date = get_date_range(date_filter, start_date_str, end_date_str)
    
    # Get IDs of orders that contain at least one item from this vendor
    vendor_order_item_qs = OrderItem.objects.filter(
        product_variant__product__vendor=vendor,
        is_deleted=False
    )
    
    if start_date:
        vendor_order_item_qs = vendor_order_item_qs.filter(order__order_date__gte=start_date)
    if end_date:
        vendor_order_item_qs = vendor_order_item_qs.filter(order__order_date__lte=end_date)
        
    vendor_order_ids = vendor_order_item_qs.values_list('order_id', flat=True).distinct()
    
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
    
    if request.GET.get('export') == 'csv' or request.GET.get('export') == 'pdf':
        for order in orders:
            items = getattr(order, 'vendor_items', order.items.filter(product_variant__product__vendor=vendor))
            order.vendor_items_display = ", ".join([f"{item.quantity}x {item.product_variant.product.name} ({item.product_variant.size.size_label}/{item.product_variant.color.name})" for item in items])

        fields = [
            ('pk', 'Order ID'),
            ('customer.user.get_full_name', 'Customer'),
            ('vendor_items_display', 'Items'),
            ('shipping_address.address_line1', 'Address Line 1'),
            ('shipping_address.address_line2', 'Address Line 2'),
            ('shipping_address.city', 'City'),
            ('shipping_address.state', 'State'),
            ('shipping_address.postal_code', 'Pincode'),
            ('vendor_total', 'Amount'),
            ('order_date', 'Date')
        ]
        if request.GET.get('export') == 'csv':
            return export_to_csv(orders, 'vendor_orders', fields)
        return export_to_pdf(orders, 'vendor_orders', fields)
    
    context = {
        'orders': orders_page,
        'search_query': q,
        'current_status': status,
        'current_sort': sort,
        'current_filter': date_filter,
        'start_date': start_date_str,
        'end_date': end_date_str,
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
    q = request.GET.get('q', '')
    categories = Category.objects.filter(is_deleted=False).select_related('parent_category')
    
    if request.GET.get('export') == 'csv':
        fields = [
            ('name', 'Category Name'),
            ('parent_category.name', 'Parent Category'),
            ('description', 'Description')
        ]
        return export_to_csv(categories, 'vendor_categories', fields)
    elif request.GET.get('export') == 'pdf':
        fields = [
            ('name', 'Category Name'),
            ('parent_category.name', 'Parent Category'),
            ('description', 'Description')
        ]
        return export_to_pdf(categories, 'vendor_categories', fields)
        
    return render(request, 'vendor_categories.html', {'categories': categories})

@vendor_required
def vendor_shipments(request):
    vendor = request.user.vendor_profile
    
    # Filtering parameters
    q = request.GET.get('q', '')
    status = request.GET.get('status', '')
    order_id = request.GET.get('order_id', '')
    sort = request.GET.get('sort', 'shipped_newest')
    date_filter = request.GET.get('date_filter', 'all')
    start_date_str = request.GET.get('start_date', '')
    end_date_str = request.GET.get('end_date', '')
    
    start_date, end_date = get_date_range(date_filter, start_date_str, end_date_str)
    
    # Fetch real shipments for this vendor
    shipments = Shipment.objects.filter(
        vendor=vendor,
        is_deleted=False
    ).select_related(
        'order_item', 'order_item__order', 'order_item__product_variant',
        'order_item__product_variant__product', 'order_item__product_variant__size',
        'order_item__product_variant__color'
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
    
    if request.GET.get('export'):
        # Prepare data for export with merged item details
        # MUST convert to list to persist runtime attributes like item_display
        shipments_list = list(shipments)
        for shipment in shipments_list:
            item = shipment.order_item
            variant = item.product_variant
            shipment.item_display = f"{item.quantity} x {variant.product.name} ({variant.size.size_label}/{variant.color.name})"

        fields = [
            ('order_item.order.pk', 'Order ID'),
            ('order_item.order.customer.user.get_full_name', 'Customer'),
            ('tracking_number', 'Tracking Number'),
            ('courier_name', 'Courier'),
            ('item_display', 'Items'),
            ('status', 'Status'),
            ('shipped_at', 'Shipped At'),
            ('expected_delivery', 'Expected Delivery')
        ]
        
        if request.GET.get('export') == 'csv':
            return export_to_csv(shipments_list, 'vendor_shipments', fields)
        elif request.GET.get('export') == 'pdf':
            return export_to_pdf(shipments_list, 'vendor_shipments', fields)
    
    context = {
        'shipments': shipments_page,
        'search_query': q,
        'order_id_filter': order_id,
        'vendor_order_ids': vendor_order_ids,
        'current_status': status,
        'current_sort': sort,
        'current_filter': date_filter,
        'start_date': start_date_str,
        'end_date': end_date_str,
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
            
            # Send Shipment Update Email
            from utils.emails import send_shipment_update_email
            send_shipment_update_email(shipment)
            
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
    vendor = request.user.vendor_profile
    
    analytics = MockObj(
        total_sales=f"₹{total_sales:,.2f}",
        sales_growth="N/A",  # Growth calculation requires prev period comparison
        total_orders=str(total_orders),
        orders_growth="N/A",
        avg_order_value=f"₹{avg_order_val:,.2f}",
        aov_growth="N/A",
        products_sold=str(products_sold),
        products_sold_growth="N/A"
    )
    
    # Graph Data: Weekly (Last 7 Days)
    weekly_labels = []
    weekly_data = []
    for i in range(6, -1, -1):
        day = now - timedelta(days=i)
        weekly_labels.append(day.strftime('%a'))
        day_revenue = base_qs.filter(
            order__order_date__date=day.date()
        ).aggregate(total=Sum(F('price') * F('quantity')))['total'] or 0
        weekly_data.append(float(day_revenue))

    # Graph Data: Yearly (current year)
    yearly_labels = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    yearly_data = []
    for month in range(1, 13):
        month_revenue = base_qs.filter(
            order__order_date__year=now.year,
            order__order_date__month=month
        ).aggregate(total=Sum(F('price') * F('quantity')))['total'] or 0
        yearly_data.append(float(month_revenue))

    context = {
        'analytics': analytics,
        'graph_data': {
            'weekly': {'labels': weekly_labels, 'data': weekly_data},
            'yearly': {'labels': yearly_labels, 'data': yearly_data}
        }
    }
    return render(request, 'vendor_analytics.html', context)

@vendor_required
def vendor_help(request):
    return render(request, 'vendor_help.html')

from store.models import Review

@vendor_required
def vendor_reviews(request):
    search_query = request.GET.get('q', '')
    rating_filter = request.GET.get('rating', '')
    sort = request.GET.get('sort', 'newest')
    
    # Fetch Reviews for Products belonging to this Vendor
    reviews = Review.objects.filter(
        product__vendor=request.user.vendor_profile,
        is_deleted=False
    ).select_related('product', 'customer__user').prefetch_related('media')
    
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
    
    if request.GET.get('export') == 'csv':
        fields = [
            ('product.name', 'Product'),
            ('customer.user.get_full_name', 'Customer'),
            ('rating', 'Rating'),
            ('comment', 'Comment'),
            ('created_at', 'Date')
        ]
        return export_to_csv(reviews, 'vendor_reviews', fields)
    elif request.GET.get('export') == 'pdf':
        fields = [
            ('product.name', 'Product'),
            ('customer.user.get_full_name', 'Customer'),
            ('rating', 'Rating'),
            ('comment', 'Comment'),
            ('created_at', 'Date')
        ]
        return export_to_pdf(reviews, 'vendor_reviews', fields)
    
    context = {
        'reviews': reviews,
        'search_query': search_query,
        'rating_filter': rating_filter,
        'current_sort': sort
    }
    return render(request, 'vendor_reviews.html', context)


@vendor_required
def vendor_sizes(request):
    q = request.GET.get('q', '')
    sizes = Size.objects.all()
    
    sizes = sizes.order_by('size_label')
    
    if request.GET.get('export') == 'csv':
        fields = [('size_label', 'Size Label')]
        return export_to_csv(sizes, 'vendor_sizes', fields)
    elif request.GET.get('export') == 'pdf':
        fields = [('size_label', 'Size Label')]
        return export_to_pdf(sizes, 'vendor_sizes', fields)
        
    return render(request, 'vendor_sizes.html', {'sizes': sizes})

@vendor_required
def vendor_colors(request):
    q = request.GET.get('q', '')
    colors = Color.objects.all()
    
    colors = colors.order_by('name')
    
    if request.GET.get('export') == 'csv':
        fields = [('name', 'Color Name'), ('hex_code', 'Hex Code')]
        return export_to_csv(colors, 'vendor_colors', fields)
    elif request.GET.get('export') == 'pdf':
        fields = [('name', 'Color Name'), ('hex_code', 'Hex Code')]
        return export_to_pdf(colors, 'vendor_colors', fields)
        
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
@vendor_required
def vendor_reports(request):
    reports = {k: v['name'] for k, v in REPORT_CONFIG.items() if not v.get('admin_only')}
    return render(request, 'vendor_reports.html', {'available_reports': reports})

@vendor_required
def vendor_reports_data(request):
    report_type = request.GET.get('report_type')
    config = REPORT_CONFIG.get(report_type)
    
    if not config or config.get('admin_only'):
        return JsonResponse({'error': 'Invalid report type'}, status=400)
    
    if 'get_filters' in request.GET:
        filters = []
        for f in config['filters']:
            if f.get('admin_only'): continue
            filters.append({
                'name': f['name'],
                'type': f['type'],
                'label': f.get('label') or f['name'].replace('_', ' ').title(),
                'placeholder': f.get('placeholder', ''),
                'options': f['options']() if callable(f.get('options')) else f.get('options', [])
            })
        return JsonResponse({'filters': filters})
    
    # Process filters from GET
    params = {}
    for f in config['filters']:
        val = request.GET.get(f['name'])
        if val and val != 'all':
            params[f['name']] = val
            
    # Add date range
    start_date, end_date = get_date_range(
        request.GET.get('date_filter', 'all'),
        request.GET.get('start_date'),
        request.GET.get('end_date')
    )
    if start_date: params['start_date'] = start_date
    if end_date: params['end_date'] = end_date
    
    is_export = request.GET.get('export') in ['csv', 'pdf']
    res = config['func'](vendor=request.user.vendor_profile, is_export=is_export, **params)
    data = res['data'] if isinstance(res, dict) else res
    columns = res['columns'] if isinstance(res, dict) else []
    
    if request.GET.get('export') in ['csv', 'pdf']:
        if not data: return HttpResponse("No data to export", status=400)
        
        # Sanitize data: Strip HTML tags for clean CSV/PDF export
        sanitized_data = []
        for row in data:
            clean_row = {}
            for k, v in row.items():
                if isinstance(v, str) and '<' in v and '>' in v:
                    clean_row[k] = strip_tags(v).strip()
                else:
                    clean_row[k] = v
            sanitized_data.append(clean_row)
            
        fields = [(k, k) for k in sanitized_data[0].keys()]
        class DataObj:
            def __init__(self, d):
                for k, v in d.items(): setattr(self, k, v)
        export_data = [DataObj(d) for d in sanitized_data]
        if request.GET.get('export') == 'pdf':
            return export_to_pdf(export_data, f'vendor_{report_type}_report', fields)
        return export_to_csv(export_data, f'vendor_{report_type}_report', fields)
        
    return JsonResponse({
        'data': data,
        'columns': columns
    })
