from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)

@register.filter
def multiply(value, arg):
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def mask_email(email):
    """
    Masks an email address.
    Example: johndoe@example.com -> j***e@example.com
    """
    if not email or "@" not in email:
        return email
    
    try:
        user_part, domain_part = email.split("@", 1)
        if len(user_part) <= 2:
            masked_user = user_part[0] + "***"
        else:
            masked_user = user_part[0] + "***" + user_part[-1]
        
        return f"{masked_user}@{domain_part}"
    except Exception:
        return email

@register.filter
def mask_phone(phone):
    """
    Masks a phone number, keeping only the last 3 digits visible.
    Example: +919876543210 -> *******210
    """
    if not phone:
        return phone
    
    phone_str = str(phone).strip()
    if len(phone_str) <= 3:
        return "***"
    
    visible_digits = 3
    masked_part = "*" * (len(phone_str) - visible_digits)
    return masked_part + phone_str[-visible_digits:]
