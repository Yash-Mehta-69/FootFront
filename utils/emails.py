import logging
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings

logger = logging.getLogger(__name__)

def get_absolute_image_url(image_field, fallback_field=None):
    """
    Helper to get absolute image URL for email templates.
    Checks Cloudinary vs Local and applies fallbacks.
    """
    img = image_field if image_field else fallback_field
    if not img:
        return ""
        
    url = img.url
    if url.startswith('http'):
        return url
        
    # Local FileSystemStorage path - needs domain
    site_url = getattr(settings, 'SITE_URL', 'http://127.0.0.1:8000')
    return f"{site_url.rstrip('/')}{url}"

def send_order_confirmation_email(order):
    """
    Sends an order confirmation email to the customer with absolute product images.
    """
    subject = f'Order Confirmed - #{order.id} | FootFront'
    from_email = settings.DEFAULT_FROM_EMAIL
    to_email = order.customer.user.email
    
    items = order.items.all()
    customer_name = order.customer.user.get_full_name()
    
    processed_items = []
    for item in items:
        # Get absolute image URL with fallback to main product image
        variant = item.product_variant
        image_url = get_absolute_image_url(variant.image, variant.product.product_image)
        
        processed_items.append({
            'product_variant': variant,
            'quantity': item.quantity,
            'price': item.price,
            'image_url': image_url
        })
    
    context = {
        'order': order,
        'items': processed_items,
        'customer_name': customer_name,
        'logo_url': f"{getattr(settings, 'SITE_URL', 'http://127.0.0.1:8000').rstrip('/')}/static/favicon.png"
    }
    
    html_content = render_to_string('emails/order_confirmation.html', context)
    text_content = strip_tags(html_content)
    
    msg = EmailMultiAlternatives(subject, text_content, from_email, [to_email])
    msg.attach_alternative(html_content, "text/html")
    
    try:
        msg.send()
        logger.info(f"Order confirmation email sent to {to_email} for order #{order.id}")
        return True
    except Exception as e:
        logger.error(f"Failed to send order confirmation email to {to_email}: {str(e)}")
        return False

def send_shipment_update_email(shipment):
    """
    Sends a shipment update email with the product image.
    """
    subject = f'Shipment Update - Order #{shipment.order_item.order.id} | FootFront'
    from_email = settings.DEFAULT_FROM_EMAIL
    to_email = shipment.order_item.order.customer.user.email
    
    customer_name = shipment.order_item.order.customer.user.get_full_name()
    
    # Get absolute image URL for shipment update
    variant = shipment.order_item.product_variant
    image_url = get_absolute_image_url(variant.image, variant.product.product_image)
    
    # Logo URL
    site_url = getattr(settings, 'SITE_URL', 'http://127.0.0.1:8000')
    logo_url = f"{site_url.rstrip('/')}/static/favicon.png"

    context = {
        'shipment': shipment,
        'customer_name': customer_name,
        'image_url': image_url,
        'logo_url': logo_url
    }
    
    html_content = render_to_string('emails/shipment_update.html', context)
    text_content = strip_tags(html_content)
    
    msg = EmailMultiAlternatives(subject, text_content, from_email, [to_email])
    msg.attach_alternative(html_content, "text/html")
    
    try:
        msg.send()
        logger.info(f"Shipment update email sent to {to_email} for shipment #{shipment.id}")
        return True
    except Exception as e:
        logger.error(f"Failed to send shipment update email to {to_email}: {str(e)}")
        return False
