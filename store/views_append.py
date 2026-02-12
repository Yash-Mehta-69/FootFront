
from utils.pdf_generator import render_to_pdf

@login_required(login_url='login')
def download_invoice(request, order_id):
    user = request.user
    
    # 1. Fetch Order
    try:
        if user.role == 'admin' or user.is_staff or user.is_superuser:
             order = Order.objects.select_related('customer', 'shipping_address', 'payment', 'customer__user').get(pk=order_id, is_deleted=False)
        elif user.role == 'vendor':
             # Vendor can only see orders that contain their products
             if not hasattr(user, 'vendor_profile'):
                 messages.error(request, "Vendor profile not found.")
                 return redirect('vendor_dashboard')
                 
             vendor = user.vendor_profile
             # Verify if this order has items from this vendor
             has_items = OrderItem.objects.filter(order_id=order_id, product_variant__product__vendor=vendor).exists()
             if not has_items:
                  messages.error(request, "Unauthorized access to this order.")
                  return redirect('vendor_orders')
             
             order = Order.objects.select_related('customer', 'shipping_address', 'payment', 'customer__user').get(pk=order_id, is_deleted=False)
        else:
             # Customer
             customer = user.customer_profile
             order = Order.objects.select_related('customer', 'shipping_address', 'payment', 'customer__user').get(pk=order_id, customer=customer, is_deleted=False)
             
    except (Order.DoesNotExist, Customer.DoesNotExist):
        messages.error(request, "Order not found or unauthorized.")
        return redirect('home')

    # 2. Fetch Items
    # For Vendor, we might want to show ONLY their items or ALL items? 
    # Usually an invoice is for the whole order for the Customer. 
    # For Vendor, they might want a packing slip, but the request says "Invoice".
    # If it's a platform invoice, it should show everything.
    # Let's assume the full invoice is generated for everyone for now, as it's "Download Invoice".
    items = order.items.filter(is_deleted=False).select_related('product_variant', 'product_variant__product', 'product_variant__color', 'product_variant__size')

    # 3. Context
    context = {
        'order': order,
        'items': items,
    }
    
    # 4. Render PDF
    pdf = render_to_pdf('utils/invoice.html', context)
    if pdf:
        response = HttpResponse(pdf, content_type='application/pdf')
        filename = f"Invoice_{order.id}.pdf"
        content = f"inline; filename='{filename}'"
        response['Content-Disposition'] = content
        return response
    
    return HttpResponse("Not Found")
