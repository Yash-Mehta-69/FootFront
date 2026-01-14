from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Cart, CartItem, Wishlist
from store.models import Product, ProductVariant

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
    item = get_object_or_404(CartItem, id=item_id, cart__customer=request.user.customer_profile)
    item.delete()
    return redirect('cart_detail')

@login_required(login_url='login')
def wishlist_detail(request):
    wishlist_items = Wishlist.objects.filter(customer=request.user.customer_profile, is_deleted=False)
    return render(request, 'wishlist.html', {'items': wishlist_items})

@login_required(login_url='login')
def checkout(request):
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
    return render(request, 'checkout.html', context)
