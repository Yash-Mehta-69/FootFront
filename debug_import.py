import os
import django
import sys

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'FootFront.settings')
django.setup()

print("Django setup complete.")

try:
    from django.core.mail import send_mail
    print("django.core.mail import success.")
except Exception as e:
    print(f"django.core.mail import failed: {e}")

try:
    from utils.emails import send_order_confirmation_email
    print("utils.emails import success.")
except Exception as e:
    print(f"utils.emails import failed: {e}")
    import traceback
    traceback.print_exc()
