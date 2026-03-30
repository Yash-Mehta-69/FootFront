from django.db.models import Count, Sum, F, Q, Avg
from store.models import Category, Product, ProductVariant, Size, Color, Review, Customer, Complaint, AttributeRequest
from vendor.models import Vendor
from cart.models import Order, OrderItem, Shipment
from django.utils import timezone
from datetime import timedelta
import html

def get_img_html(url, alt="", size=32, is_circle=False, border=True):
    style = f"width:{size}px; height:{size}px; object-fit:cover;"
    if border: style += " border:1px solid rgba(0,0,0,0.1);"
    if is_circle: style += " border-radius:50%;"
    else: style += " border-radius:6px;"
    return f'<div class="rounded-1 bg-light" style="width:{size}px; height:{size}px; overflow:hidden; flex-shrink:0; {"border:1px solid rgba(0,0,0,0.1);" if border else ""}"><img src="{url}" alt="{html.escape(alt)}" style="width:100%; height:100%; object-fit:cover;"></div>'

def get_badge_html(text, status="primary"):
    status_map = {
        'active': 'status-active',
        'shipped': 'text-primary-custom',
        'in_transit': 'text-primary-custom',
        'preparing': 'status-warning',
        'delivered': 'text-success-custom',
        'cancelled': 'text-danger-custom',
        'blocked': 'status-inactive',
        'resolved': 'text-success-custom',
        'pending': 'status-warning',
        'completed': 'text-success-custom',
        'paid': 'text-success-custom',
        'failed': 'text-danger-custom',
    }
    
    clean_text = text.lower().replace(' ', '_')
    cls = status_map.get(clean_text, 'text-muted')
    
    icon_map = {
        'active': '<i class="fas fa-check-circle me-1"></i>',
        'delivered': '<i class="fas fa-check-circle me-1"></i>',
        'paid': '<i class="fas fa-check-circle me-1"></i>',
        'preparing': '<i class="fas fa-clock me-1"></i>',
        'pending': '<i class="fas fa-clock me-1"></i>',
        'shipped': '<i class="fas fa-truck me-1"></i>',
        'in_transit': '<i class="fas fa-truck me-1"></i>',
        'failed': '<i class="fas fa-times-circle me-1"></i>',
        'blocked': '<i class="fas fa-ban me-1"></i>',
    }
    icon = icon_map.get(clean_text, '')
    
    if 'status-' in cls:
        return f'<span class="status-badge {cls}">{icon}{text.upper()}</span>'
    else:
        return f'<div class="{cls} small fw-bold">{icon}{text.upper()}</div>'

def get_stars_html(rating):
    stars = ""
    for i in range(1, 6):
        if i <= rating:
            stars += '<i class="fas fa-star" style="color:#ffc107; font-size:12px;"></i>'
        else:
            stars += '<i class="far fa-star" style="color:#ffc107; font-size:12px;"></i>'
    return f'<span class="text-nowrap">{stars}</span>'

def get_products_report(vendor=None, is_export=False, **filters):
    qs = Product.objects.filter(is_deleted=False).select_related('category', 'vendor').prefetch_related('productvariant_set', 'productvariant_set__size', 'productvariant_set__color')
    if vendor: qs = qs.filter(vendor=vendor)
    elif filters.get('vendor_id'): qs = qs.filter(vendor_id=filters.get('vendor_id'))

    q = filters.get('q')
    if q: qs = qs.filter(Q(name__icontains=q) | Q(category__name__icontains=q) | Q(vendor__shopName__icontains=q))

    category = filters.get('category')
    if category and category != 'all': qs = qs.filter(category_id=category)
    gender = filters.get('gender')
    if gender and gender != 'all': qs = qs.filter(gender=gender)

    start_date = filters.get('start_date')
    end_date = filters.get('end_date')
    if start_date: qs = qs.filter(created_at__gte=start_date)
    if end_date: qs = qs.filter(created_at__lte=end_date)
        
    qs = qs.annotate(min_price=Avg('productvariant__price'), total_stk=Sum('productvariant__stock'), variant_count=Count('productvariant'))

    sort = filters.get('sort')
    if sort == 'price_low': qs = qs.order_by('min_price')
    elif sort == 'price_high': qs = qs.order_by('-min_price')
    elif sort == 'stock_low': qs = qs.order_by('total_stk')
    elif sort == 'stock_high': qs = qs.order_by('-total_stk')
    else: qs = qs.order_by('-created_at')

    data = []
    if is_export:
        columns = ['Product Name', 'Category', 'Size', 'Color', 'Price', 'Stock', 'Gender', 'Is Trending', 'Date Created']
        if not vendor: columns.insert(2, 'Vendor')
        for i in qs:
            for v in i.productvariant_set.all():
                row = {
                    'Product Name': i.name,
                    'Category': i.category.name if i.category else 'N/A',
                    'Size': v.size.size_label if v.size else '-',
                    'Color': v.color.name if v.color else '-',
                    'Price': f"Rs. {float(v.price):.2f}",
                    'Stock': v.stock if v.stock > 0 else '-',
                    'Gender': i.get_gender_display(),
                    'Is Trending': "True" if i.is_trending else "False",
                    'Date Created': i.created_at.strftime('%Y-%m-%d %H:%M')
                }
                if not vendor: row['Vendor'] = i.vendor.shopName if i.vendor else "Admin"
                data.append(row)
    else:
        columns = ['Product', 'Vendor', 'Category', 'Gender', 'Price', 'Stock', 'Status'] if not vendor else ['Product', 'Category', 'Gender', 'Price', 'Stock', 'Status']
        for i in qs:
            prod_html = f'<div class="d-flex flex-column"><div class="fw-bold" style="color:var(--text-main); font-size:0.9rem;">{i.name}</div>'
            if i.is_trending: prod_html += f'<div style="margin-top:2px;"><span class="badge bg-warning text-dark border-0 rounded-pill" style="font-size:10px; padding:2px 8px; font-weight:600;">Trending</span></div>'
            prod_html += '</div>'
            
            variants = i.productvariant_set.all()
            stock_html = f'<div class="d-flex flex-column gap-1"><div class="text-muted small mb-1" style="font-size:11px;">{i.variant_count} Variants</div>'
            var_imgs_html = '<div class="d-flex gap-1 flex-wrap">'
            added_variant_imgs = set()
            for v in variants:
                if v.image and v.image.url not in added_variant_imgs:
                    var_imgs_html += get_img_html(v.image.url, "", size=26, border=True)
                    added_variant_imgs.add(v.image.url)
            var_imgs_html += '</div>'
            stock_html += var_imgs_html + '</div>'
            
            row = {
                'Product': prod_html,
                'Category': i.category.name if i.category else 'N/A',
                'Gender': i.get_gender_display(),
                'Price': f'<span class="fw-bold" style="font-size:1rem; color:var(--text-main);">₹{float(i.min_price or 0):,.2f}</span>',
                'Stock': stock_html,
                'Status': get_badge_html('Active' if not i.is_deleted else 'Deleted', 'active')
            }
            if not vendor: row['Vendor'] = f'<div class="fw-bold text-truncate" style="max-width:15ch; color:var(--text-main);">{i.vendor.shopName if i.vendor else "Admin"}</div>'
            data.append(row)
    return {'columns': columns, 'data': data}

def get_categories_report(vendor=None, **filters):
    qs = Category.objects.filter(is_deleted=False).select_related('parent_category').annotate(p_count=Count('product'))
    q = filters.get('q')
    if q: qs = qs.filter(Q(name__icontains=q) | Q(slug__icontains=q))
    if not vendor: columns = ['Image', 'Name', 'Parent Category', 'Description', 'Products', 'Status']
    else: columns = ['Image', 'Category Name', 'Parent Category', 'Description', 'Products']
    
    data = []
    for c in qs:
        img_url = c.cat_image.url if c.cat_image else "/static/images/placeholder.png"
        row = {
            'Image': get_img_html(img_url, c.name, size=40),
            'Name': f'<strong>{c.name}</strong>',
            'Category Name': f'<strong>{c.name}</strong>',
            'Parent Category': f'<span class="badge" style="background:rgba(var(--primary-rgb), 0.1); color:var(--primary-color); border-radius:6px; padding:4px 8px;">{c.parent_category.name}</span>' if c.parent_category else '<span class="text-muted small">Top Level</span>',
            'Description': (c.description[:60] + '...') if (c.description and len(c.description) > 60) else (c.description or '-'),
            'Products': f'<span class="badge rounded-pill bg-secondary" style="font-size:10px;">{c.p_count} Products</span>',
            'Status': get_badge_html('Active', 'active')
        }
        data.append(row)
    return {'columns': columns, 'data': data}

def get_orders_report(vendor=None, is_export=False, **filters):
    if vendor: items_qs = OrderItem.objects.filter(product_variant__product__vendor=vendor, is_deleted=False)
    else: 
        items_qs = OrderItem.objects.filter(is_deleted=False)
        if filters.get('vendor_id'): items_qs = items_qs.filter(product_variant__product__vendor_id=filters.get('vendor_id'))

    start_date = filters.get('start_date')
    end_date = filters.get('end_date')
    if start_date: items_qs = items_qs.filter(order__order_date__gte=start_date)
    if end_date: items_qs = items_qs.filter(order__order_date__lte=end_date)
    q = filters.get('q')
    if q: items_qs = items_qs.filter(Q(order__pk__icontains=q.replace('#ORD-', '')) | Q(order__customer__user__first_name__icontains=q) | Q(order__customer__user__last_name__icontains=q))

    data = []
    if is_export:
        columns = ['Order ID', 'Customer', 'Product', 'Variant (Size/Color)', 'Qty', 'Unit Price', 'Total', 'Payment', 'Fulfillment', 'Date']
        if not vendor: columns.insert(2, 'Vendor')
        
        items = items_qs.select_related('order', 'order__customer', 'order__customer__user', 'order__payment', 'product_variant', 'product_variant__product', 'product_variant__product__vendor', 'product_variant__size', 'product_variant__color', 'shipment').order_by('-order__order_date')
        
        for it in items:
            row = {
                'Order ID': f"#ORD-{it.order.id}",
                'Customer': it.order.customer.user.get_full_name(),
                'Product': it.product_variant.product.name,
                'Variant (Size/Color)': f"{it.product_variant.size.size_label} / {it.product_variant.color.name}",
                'Qty': it.quantity,
                'Unit Price': f"Rs. {float(it.price):.2f}",
                'Total': f"Rs. {float(it.price * it.quantity):.2f}",
                'Payment': it.order.payment.status.upper() if it.order.payment else 'PENDING',
                'Fulfillment': it.shipment.get_status_display().upper() if it.shipment else 'PENDING',
                'Date': it.order.order_date.strftime('%Y-%m-%d %H:%M')
            }
            if not vendor: row['Vendor'] = it.product_variant.product.vendor.shopName if it.product_variant.product.vendor else "Admin"
            data.append(row)
    else:
        order_ids = items_qs.values_list('order_id', flat=True).distinct()
        orders = Order.objects.filter(id__in=order_ids).select_related('customer', 'customer__user', 'payment').prefetch_related('items', 'items__shipment', 'items__product_variant__product__vendor')
        sort = filters.get('sort')
        orders = orders.order_by('order_date' if sort == 'date_oldest' else '-order_date')

        if not vendor: columns = ['Order ID', 'Customer', 'Items', 'Vendor', 'Payment Info', 'Fulfillment', 'Earnings (7%)', 'Date']
        else: columns = ['Order ID', 'Customer', 'Items', 'Price', 'Payment', 'Fulfillment Status', 'Date']

        for o in orders:
            items_html = '<div class="d-flex flex-column gap-1">'
            target_items = [it for it in o.items.all() if not vendor or it.product_variant.product.vendor == vendor]
            for it in target_items[:2]:
                it_img = it.product_variant.image.url if it.product_variant.image else (it.product_variant.product.product_image.url if it.product_variant.product.product_image else "")
                items_html += f'<div class="d-flex align-items-center gap-2">{get_img_html(it_img, "", size=28)} <div class="small text-truncate fw-bold" style="max-width:12ch; color:var(--text-main); font-size:0.75rem;">{it.product_variant.product.name}</div></div>'
            if len(target_items) > 2: items_html += f'<div class="text-primary-custom fw-bold" style="font-size:9px; margin-left:2px;">+{len(target_items)-2} MORE ITEMS</div>'
            items_html += '</div>'
            pay_status = o.payment.status if o.payment else 'pending'
            price_val = o.total_amount if not vendor else sum(it.price * it.quantity for it in target_items)
            pay_html = f'<div><div class="fw-bold text-primary-custom">₹{float(price_val):,.2f}</div>{get_badge_html(pay_status)}</div>'
            full_status = target_items[0].shipment.get_status_display() if (target_items and target_items[0].shipment) else 'Pending'
            row = {
                'Order ID': f'<div class="fw-bold text-primary-custom">#ORD-{o.pk}</div>',
                'Customer': f'<div class="fw-bold" style="color:var(--text-main);">{o.customer.user.get_full_name()}</div><div class="small text-muted">{o.customer.user.email}</div>',
                'Items': items_html,'Payment Info': pay_html,'Payment': pay_html,'Price': f"₹{float(price_val):,.2f}",
                'Fulfillment': get_badge_html(full_status),'Fulfillment Status': get_badge_html(full_status),
                'Date': f'<div class="small" style="color:var(--text-main);">{o.order_date.strftime("%d %b, %Y")}</div><div class="text-muted small">{o.order_date.strftime("%H:%M")}</div>'
            }
            if not vendor:
                v_list = ", ".join(list(set([it.product_variant.product.vendor.shopName for it in o.items.all() if it.product_variant.product.vendor])))
                row['Vendor'] = f'<div class="fw-bold text-truncate" style="max-width:15ch; color:var(--text-main);">{v_list or "Admin"}</div>'
                row['Earnings (7%)'] = f'<div class="fw-bold text-success-custom">₹{float(o.total_amount)*0.07:,.2f}</div><div class="small text-muted" style="font-size:0.7rem;">(7% Comm.)</div>'
            data.append(row)
    return {'columns': columns, 'data': data}

def get_shipments_report(vendor=None, **filters):
    qs = Shipment.objects.filter(is_deleted=False).select_related('order_item', 'order_item__order', 'order_item__product_variant__product', 'order_item__product_variant__product__vendor')
    if vendor: qs = qs.filter(vendor=vendor)
    elif filters.get('vendor_id'): qs = qs.filter(vendor_id=filters.get('vendor_id'))
    q = filters.get('q')
    if q: qs = qs.filter(Q(tracking_number__icontains=q) | Q(order_item__order__pk__icontains=q.replace('#ORD-', '')) | Q(order_item__product_variant__product__name__icontains=q))
    status = filters.get('status')
    if status: qs = qs.filter(status=status)
    if not vendor: columns = ['Order ID', 'Product Item', 'Vendor', 'Tracking #', 'Courier', 'Fulfillment', 'Timeline']
    else: columns = ['Order ID', 'Product', 'Tracking #', 'Courier', 'Status', 'Shipped Date', 'Est. Delivery']
    data = []
    for s in qs:
        it_img = s.order_item.product_variant.image.url if s.order_item.product_variant.image else (s.order_item.product_variant.product.product_image.url if s.order_item.product_variant.product.product_image else "")
        prod_html = f'<div class="d-flex align-items-center gap-2">{get_img_html(it_img, "", size=32)} <div><div class="fw-bold" style="color:var(--text-main); font-size:0.9rem;">{s.order_item.product_variant.product.name}</div><div class="small text-muted" style="font-size:0.75rem;">{s.order_item.product_variant.size.size_label} / {s.order_item.product_variant.color.name}</div></div></div>'
        row = {
            'Order ID': f'<div class="fw-bold text-primary-custom">#ORD-{s.order_item.order.id}</div>','Product Item': prod_html,'Product': prod_html,
            'Tracking #': f'<span class="font-monospace small fw-bold" style="color:var(--text-main);">{s.tracking_number or "-"}</span>',
            'Courier': s.courier_name or '-','Fulfillment': get_badge_html(s.get_status_display()),'Status': get_badge_html(s.get_status_display()),
            'Timeline': f'<div class="small"><span class="text-muted">Shipped:</span> {s.shipped_at.strftime("%d %b") if s.shipped_at else "TBA"}<br><span class="text-muted">Est:</span> {s.expected_delivery.strftime("%d %b") if s.expected_delivery else "TBA"}</div>',
            'Shipped Date': s.shipped_at.strftime('%d %b, %Y') if s.shipped_at else '-','Est. Delivery': s.expected_delivery.strftime('%d %b, %Y') if s.expected_delivery else '-'
        }
        if not vendor: row['Vendor'] = f'<div class="fw-bold text-truncate" style="max-width:15ch; color:var(--text-main);">{s.vendor.shopName if s.vendor else "Admin"}</div>'
        data.append(row)
    return {'columns': columns, 'data': data}

def get_reviews_report(vendor=None, **filters):
    qs = Review.objects.filter(is_deleted=False).select_related('product', 'customer', 'customer__user').prefetch_related('media')
    if vendor: qs = qs.filter(product__vendor=vendor)
    elif filters.get('vendor_id'): qs = qs.filter(product__vendor_id=filters.get('vendor_id'))
    q = filters.get('q')
    if q: qs = qs.filter(Q(product__name__icontains=q) | Q(customer__user__first_name__icontains=q) | Q(customer__user__last_name__icontains=q))
    rating = filters.get('rating')
    if rating: qs = qs.filter(rating=rating)
    columns = ['Product', 'User', 'Rating', 'Comment', 'Media', 'Date']
    data = []
    for r in qs:
        prod_img = r.product.product_image.url if r.product.product_image else ""
        prod_html = f'<div class="d-flex align-items-center gap-2">{get_img_html(prod_img, "", size=30)} <span class="fw-bold" style="color:var(--text-main);">{r.product.name}</span></div>'
        avatar_url = r.customer.user.profile_picture.url if (hasattr(r.customer.user, 'profile_picture') and r.customer.user.profile_picture) else f"https://ui-avatars.com/api/?name={r.customer.user.first_name}+{r.customer.user.last_name}"
        user_html = f'<div class="d-flex align-items-center gap-2">{get_img_html(avatar_url, "", size=30, is_circle=True)} <div><div class="fw-bold">{r.customer.user.get_full_name()}</div></div></div>'
        media_html = '<div class="d-flex gap-1">'
        for m in r.media.all()[:3]:
            if m.media_type == 'image': media_html += get_img_html(m.file.url, "", size=28)
        if r.media.count() > 3: media_html += f'<span class="text-muted small">+{r.media.count()-3}</span>'
        media_html += '</div>' if r.media.exists() else '<span class="text-muted">-</span>'
        data.append({'Product': prod_html,'User': user_html,'Rating': get_stars_html(r.rating),'Comment': f'<div class="small" style="max-width:25ch; overflow:hidden; text-overflow:ellipsis;">{r.comment}</div>','Media': media_html,'Date': r.created_at.strftime('%d %b, %Y')})
    return {'columns': columns, 'data': data}

def get_customers_report(vendor=None, **filters):
    if vendor: return {'columns': [], 'data': []}
    qs = Customer.objects.filter(is_deleted=False).select_related('user')
    q = filters.get('q')
    if q: qs = qs.filter(Q(user__first_name__icontains=q) | Q(user__last_name__icontains=q) | Q(user__email__icontains=q))
    columns = ['Name', 'Email', 'Phone', 'Status']
    data = []
    for i in qs:
        avatar_html = f'<div class="d-flex align-items-center"><div class="user-avatar me-2" style="width:32px; height:32px; font-size:12px;">{i.user.first_name[:1]}</div>{i.user.get_full_name()}</div>'
        data.append({'Name': avatar_html,'Email': i.user.email,'Phone': i.phone or '-','Status': get_badge_html('Blocked' if i.is_blocked else 'Active', 'blocked' if i.is_blocked else 'active')})
    return {'columns': columns, 'data': data}

def get_vendors_report(vendor=None, **filters):
    if vendor: return {'columns': [], 'data': []}
    qs = Vendor.objects.filter(is_deleted=False).select_related('user')
    q = filters.get('q')
    if q: qs = qs.filter(Q(shopName__icontains=q) | Q(user__first_name__icontains=q) | Q(user__last_name__icontains=q))
    columns = ['Shop Name', 'Owner', 'Email', 'Phone', 'Status']
    data = []
    for i in qs:
        img_url = i.profile_picture.url if i.profile_picture else ""
        shop_html = f'<div class="d-flex align-items-center gap-2">{get_img_html(img_url, "", size=32, is_circle=True) if img_url else f"<div class=\'user-avatar\' style=\'width:32px;height:32px;\'>{i.shopName[:1]}</div>"} <strong>{i.shopName}</strong></div>'
        data.append({'Shop Name': shop_html,'Owner': i.user.get_full_name(),'Email': i.user.email,'Phone': i.business_phone or '-','Status': get_badge_html('Blocked' if i.is_blocked else 'Active', 'blocked' if i.is_blocked else 'active')})
    return {'columns': columns, 'data': data}

def get_complaints_report(vendor=None, **filters):
    if vendor: return {'columns': [], 'data': []}
    qs = Complaint.objects.filter(is_deleted=False).select_related('customer', 'customer__user')
    q = filters.get('q')
    if q: qs = qs.filter(Q(subject__icontains=q) | Q(customer__user__first_name__icontains=q) | Q(customer__user__last_name__icontains=q))
    columns = ['Ticket ID', 'User', 'Subject', 'Date', 'Status']
    data = []
    for c in qs:
        data.append({'Ticket ID': f'<strong class="text-primary">#{c.pk}</strong>','User': f'<div>{c.customer.user.get_full_name()}<br><small class="text-muted">{c.customer.user.email}</small></div>','Subject': f'<strong>{c.subject}</strong><p class="small text-muted mb-0">{c.description[:50]}...</p>','Date': c.created_at.strftime('%b %d, %Y'),'Status': f'<span class="badge {"bg-warning text-dark" if c.status == "Pending" else "bg-primary" if c.status == "In Progress" else "bg-success"}">{c.status}</span>'})
    return {'columns': columns, 'data': data}

def get_attribute_requests_report(vendor=None, **filters):
    if vendor: return {'columns': [], 'data': []}
    qs = AttributeRequest.objects.all().select_related('vendor', 'vendor__user')
    at_type = filters.get('type')
    if at_type: qs = qs.filter(attribute_type=at_type)
    columns = ['Vendor', 'Type', 'Requested Value', 'Date']
    data = []
    for r in qs:
        data.append({'Vendor': f'<strong>{r.vendor.shopName}</strong>','Type': f'<span class="badge bg-info-subtle text-info border border-info-subtle px-2 py-1">{r.attribute_type}</span>','Requested Value': f'<code class="fw-bold text-primary">{r.attribute_value}</code>','Date': r.created_at.strftime('%b %d, %Y')})
    return {'columns': columns, 'data': data}

def get_generic_report(model_class, **filters):
    qs = model_class.objects.all()
    if model_class == Size:
        columns = ['Size Label']
        data = [{'Size Label': f'<span class="badge border text-dark bg-light px-3 py-2">{s.size_label}</span>'} for s in qs]
    elif model_class == Color:
        columns = ['Color Preview', 'Color Name', 'Hex Code']
        data = [{'Color Preview': f'<div style="width:28px;height:28px;background:{c.hex_code};border-radius:50%;border:3px solid white;box-shadow:0 0 10px rgba(0,0,0,1);"></div>','Color Name': f'<strong>{c.name}</strong>','Hex Code': f'<code class="fw-bold">{c.hex_code.upper()}</code>'} for c in qs]
    else: columns, data = [], []
    return {'columns': columns, 'data': data}

REPORT_CONFIG = {
    'products': {'name': 'Products Report','filters': [{'name': 'q', 'type': 'text', 'placeholder': 'Search product...'},{'name': 'category', 'type': 'select', 'options': lambda: [{'id': c.id, 'name': c.name} for c in Category.objects.filter(is_deleted=False)]},{'name': 'vendor_id', 'type': 'select', 'admin_only': True, 'options': lambda: [{'id': v.id, 'name': v.shopName} for v in Vendor.objects.filter(is_deleted=False)]},{'name': 'sort', 'type': 'select', 'options': lambda: [{'id': 'newest', 'name': 'Newest First'},{'id': 'price_low', 'name': 'Price: Low to High'},{'id': 'price_high', 'name': 'Price: High to Low'}]}], 'func': get_products_report},
    'categories': {'name': 'Categories Report','filters': [{'name': 'q', 'type': 'text', 'placeholder': 'Search category...'}],'func': get_categories_report},
    'orders': {'name': 'Orders Report','filters': [{'name': 'q', 'type': 'text', 'placeholder': 'Search ID or customer...'},{'name': 'vendor_id', 'type': 'select', 'admin_only': True, 'options': lambda: [{'id': v.id, 'name': v.shopName} for v in Vendor.objects.filter(is_deleted=False)]},{'name': 'sort', 'type': 'select', 'options': lambda: [{'id': 'date_newest', 'name': 'Date: Newest'},{'id': 'date_oldest', 'name': 'Date: Oldest'}]}],'func': get_orders_report},
    'shipments': {'name': 'Shipments Report','filters': [{'name': 'q', 'type': 'text', 'placeholder': 'Search tracking...'},{'name': 'status', 'type': 'select', 'options': lambda: [{'id': s[0], 'name': s[1]} for s in Shipment.STATUS_CHOICES]},{'name': 'vendor_id', 'type': 'select', 'admin_only': True, 'options': lambda: [{'id': v.id, 'name': v.shopName} for v in Vendor.objects.filter(is_deleted=False)]}],'func': get_shipments_report},
    'reviews': {'name': 'Reviews Report','filters': [{'name': 'q', 'type': 'text', 'placeholder': 'Search product...'},{'name': 'rating', 'type': 'select', 'options': lambda: [{'id': i, 'name': f'{i} Stars'} for i in range(5, 0, -1)]}],'func': get_reviews_report},
    'sizes': {'name': 'Sizes Report','filters': [],'func': lambda **f: get_generic_report(Size, **f)},
    'colors': {'name': 'Colors Report','filters': [],'func': lambda **f: get_generic_report(Color, **f)},
    'customers': {'name': 'Customers Report','filters': [{'name': 'q', 'type': 'text', 'placeholder': 'Search name/email...'}],'func': get_customers_report,'admin_only': True},
    'vendors': {'name': 'Vendors Report','filters': [{'name': 'q', 'type': 'text', 'placeholder': 'Search shop...'}],'func': get_vendors_report,'admin_only': True},
    'complaints': {'name': 'Complaints Report','filters': [{'name': 'q', 'type': 'text', 'placeholder': 'Search ticket...'}],'func': get_complaints_report,'admin_only': True},
    'attribute_requests': {'name': 'Attr. Requests Report','filters': [{'name': 'type', 'type': 'select', 'options': lambda: [{'id': 'Category', 'name': 'Category'}, {'id': 'Size', 'name': 'Size'}, {'id': 'Color', 'name': 'Color'}]}],'func': get_attribute_requests_report,'admin_only': True}
}
