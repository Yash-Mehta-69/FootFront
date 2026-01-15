from django import template
from django.urls import reverse, NoReverseMatch
from store.models import Category
from cart.models import Cart, CartItem
from django.db.models import Sum


register = template.Library()

@register.simple_tag
def get_categories():
    """Returns all non-deleted categories."""
    return Category.objects.filter(is_deleted=False)

@register.simple_tag
def get_cart_count(request):
    """Returns the total number of items in the user's cart."""
    if not request.user.is_authenticated:
        return 0
        
    try:
        # Assuming one active cart per customer
        customer = request.user.customer_profile
        cart = Cart.objects.filter(customer=customer, is_deleted=False).first()
        if cart:
            count = cart.items.filter(is_deleted=False).aggregate(total=Sum('quantity'))['total']
            return count if count else 0
    except:
        pass
    return 0

@register.simple_tag
def get_cart_items(request):
    """Returns the items in the user's cart."""
    if not request.user.is_authenticated:
        return []
    try:
        customer = request.user.customer_profile
        cart = Cart.objects.filter(customer=customer, is_deleted=False).first()
        if cart:
            return cart.items.filter(is_deleted=False).select_related('product_variant__product', 'product_variant__color', 'product_variant__size')
    except:
        pass
    return []

@register.simple_tag
def get_cart_total(request):
    """Returns the total price of items in the cart."""
    items = get_cart_items(request)
    total = 0
    for item in items:
        total += item.product_variant.price * item.quantity
    return total


@register.simple_tag
def is_active(request, url_pattern, **kwargs):
    """Checks if the current URL matches the pattern and query params."""
    try:
        path = reverse(url_pattern)
        if request.path == path:
            # If no kwargs provided, match only if no GET params in request
            if not kwargs:
                return 'active' if not request.GET else ''
            
            # Check if additional kwargs (query params) match
            for key, value in kwargs.items():
                if request.GET.get(key) != str(value):
                    return ''
            return 'active'
    except NoReverseMatch:
        if url_pattern in request.path:
            return 'active'
    return ''

