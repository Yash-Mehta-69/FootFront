from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db.models import Sum
from django.template.loader import render_to_string
import json
import razorpay
from django.conf import settings
from .models import Cart, CartItem, Wishlist, Order, OrderItem, Payment, Shipment, ShipmentStatusHistory
from store.models import Product, ProductVariant, ShippingAddress
import os
from dotenv import load_dotenv

load_dotenv()

@login_required(login_url='login')
def cart_detail(request):
    try:
        cart = Cart.objects.get(customer=request.user.customer_profile, is_deleted=False)
        items = cart.items.filter(is_deleted=False)
        total = sum(item.product_variant.price * item.quantity for item in items)
    except Cart.DoesNotExist:
        items = []
        total = 0
        
    context = {
        'items': items,
        'total': total
    }
    return render(request, 'cart.html', context)

def add_to_cart_ajax(request):
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'message': 'login_required'})
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            variant_id = data.get('variant_id')
            quantity = int(data.get('quantity', 1))
            
            variant = get_object_or_404(ProductVariant, id=variant_id)
            
            # Stock check
            if variant.stock < quantity:
                return JsonResponse({'success': False, 'message': f'Only {variant.stock} left in stock.'})
            
            cart, created = Cart.objects.get_or_create(customer=request.user.customer_profile, is_deleted=False)
            cart_item, item_created = CartItem.objects.get_or_create(cart=cart, product_variant=variant)
            
            if not item_created:
                cart_item.quantity += quantity
            else:
                cart_item.quantity = quantity
            
            cart_item.save()
            
            # Count items in cart (quantities sum)
            cart_count = cart.items.filter(is_deleted=False).aggregate(total=Sum('quantity'))['total'] or 0
            
            # Render updated mini cart HTML
            cart_html = render_to_string('includes/mini_cart_content.html', request=request)
            
            return JsonResponse({
                'success': True, 
                'cart_count': cart_count,
                'cart_html': cart_html
            })
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})
            
    return JsonResponse({'success': False, 'message': 'Invalid request'})

@login_required(login_url='login')
def add_to_cart(request, product_id):
    # Simplified logic: just grab first variant for now or assume post data
    # Realistically needs size/color from POST
    product = get_object_or_404(Product, id=product_id)
    # Temporary: get first variant
    variant = ProductVariant.objects.filter(product=product).first()
    
    if not variant:
        return redirect('shop') # Error handling needed

    cart, created = Cart.objects.get_or_create(customer=request.user.customer_profile, is_deleted=False)
    cart_item, item_created = CartItem.objects.get_or_create(cart=cart, product_variant=variant)
    
    if not item_created:
        cart_item.quantity += 1
        cart_item.save()
        
    return redirect('cart_detail')

@login_required(login_url='login')
def remove_from_cart(request, item_id):
    from django.http import JsonResponse
    item = get_object_or_404(CartItem, id=item_id, cart__customer=request.user.customer_profile)
    item.delete()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True})
        
    return redirect('cart_detail')

@login_required(login_url='login')
def wishlist_detail(request):
    wishlist_items = Wishlist.objects.filter(customer=request.user.customer_profile, is_deleted=False)
    return render(request, 'wishlist.html', {'items': wishlist_items})

@login_required(login_url='login')
def checkout(request):
    customer = request.user.customer_profile
    try:
        cart = Cart.objects.get(customer=customer, is_deleted=False)
        items = cart.items.filter(is_deleted=False)
        if not items:
            return redirect('cart_detail')
        total = sum(item.product_variant.price * item.quantity for item in items)
    except Cart.DoesNotExist:
        return redirect('cart_detail')
    
    addresses = ShippingAddress.objects.filter(customer=customer, is_deleted=False)
    
    context = {
        'items': items,
        'total': total,
        'addresses': addresses,
        'razorpay_key_id': os.getenv('RAZORPAY_KEY_ID'),
    }
    return render(request, 'checkout.html', context)

@login_required(login_url='login')
def create_order(request):
    if request.method == 'POST':
        customer = request.user.customer_profile
        try:
            cart = Cart.objects.get(customer=customer, is_deleted=False)
            items = cart.items.filter(is_deleted=False)
            if not items:
                return JsonResponse({'success': False, 'message': 'Cart is empty'})
            total = sum(item.product_variant.price * item.quantity for item in items)
        except Cart.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Cart not found'})

        address_id = request.POST.get('address_id')
        if address_id and address_id != 'new':
            shipping_address = get_object_or_404(ShippingAddress, id=address_id, customer=customer)
        else:
            # Create new address
            address_line1 = request.POST.get('address')
            city = request.POST.get('city')
            state = request.POST.get('state')
            zipcode = request.POST.get('zipcode')
            
            if not all([address_line1, city, zipcode]):
                return JsonResponse({'success': False, 'message': 'Please provide all shipping details'})
                
            shipping_address = ShippingAddress.objects.create(
                customer=customer,
                address_line1=address_line1,
                city=city,
                state=state,
                postal_code=zipcode
            )

        # 1. Create Order
        order = Order.objects.create(
            customer=customer,
            total_amount=total,
            shipping_address=shipping_address
        )
        
        # 2. Create OrderItems
        for item in items:
            OrderItem.objects.create(
                order=order,
                product_variant=item.product_variant,
                quantity=item.quantity,
                price=item.product_variant.price
            )
        
        # 3. Razorpay Integration
        client = razorpay.Client(auth=(os.getenv('RAZORPAY_KEY_ID'), os.getenv('RAZORPAY_KEY_SECRET')))
        
        razorpay_order_data = {
            'amount': int(total * 100),
            'currency': 'INR',
            'payment_capture': '1'
        }
        
        try:
            razorpay_order = client.order.create(data=razorpay_order_data)
            razorpay_order_id = razorpay_order['id']
            
            # 4. Create Payment entry (pending)
            Payment.objects.create(
                order=order,
                amount=total,
                razorpay_order_id=razorpay_order_id,
                status='pending'
            )
            
            return JsonResponse({
                'success': True,
                'razorpay_order_id': razorpay_order_id,
                'amount': int(total * 100),
                'currency': 'INR',
                'order_id': order.id,
                'callback_url': request.build_absolute_uri(reverse('payment_callback')),
                'prefill_name': request.user.get_full_name(),
                'prefill_email': request.user.email,
                'prefill_contact': customer.phone
            })
        except Exception as e:
            return JsonResponse({'success': False, 'message': f'Razorpay Error: {str(e)}'})

    return JsonResponse({'success': False, 'message': 'Invalid request'})

@login_required(login_url='login')
def payment_callback(request):
    if request.method == "POST":
        data = request.POST
        
        client = razorpay.Client(auth=(os.getenv('RAZORPAY_KEY_ID'), os.getenv('RAZORPAY_KEY_SECRET')))
        
        params_dict = {
            'razorpay_order_id': data.get('razorpay_order_id'),
            'razorpay_payment_id': data.get('razorpay_payment_id'),
            'razorpay_signature': data.get('razorpay_signature')
        }
        
        try:
            # Verify signature
            client.utility.verify_payment_signature(params_dict)
            
            # Signature matches - Payment Success
            payment = Payment.objects.get(razorpay_order_id=data.get('razorpay_order_id'))
            payment.razorpay_payment_id = data.get('razorpay_payment_id')
            payment.razorpay_signature = data.get('razorpay_signature')
            payment.status = 'completed'
            
            # Fetch payment details to get method (card, upi, etc.)
            try:
                razor_pay_details = client.payment.fetch(payment.razorpay_payment_id)
                if razor_pay_details and 'method' in razor_pay_details:
                    payment.payment_method = razor_pay_details['method']
            except:
                pass
                
            payment.save()
            
            # 1. Create Shipments and Update Stock
            order = payment.order
            for item in order.items.all():
                # Create Shipment for each order item
                shipment = Shipment.objects.create(
                    order_item=item,
                    vendor=item.product_variant.product.vendor,
                    status='preparing',
                    tracking_number=f"TRACK-{order.id}-{item.id}", # Placeholder tracking
                    courier_name="Processing" # Initial courier status
                )
                
                # Log Initial History
                ShipmentStatusHistory.objects.create(
                    shipment=shipment,
                    status='Preparing',
                    description="Order confirmed. We're getting your item ready."
                )
                
                # Update Stock
                variant = item.product_variant
                variant.stock -= item.quantity
                variant.save()

            # 2. Clear Cart
            cart = Cart.objects.get(customer=request.user.customer_profile, is_deleted=False)
            cart.items.filter(is_deleted=False).update(is_deleted=True)
            
            return render(request, 'payment_success.html', {'payment_id': payment.razorpay_payment_id})
            
        except Exception as e:
            # Signature mismatch or other error
            return render(request, 'payment_failed.html', {'error': str(e)})
            
    return redirect('cart_detail')
