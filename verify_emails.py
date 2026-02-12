import os
import django
import sys

# Ensure project root is in path
project_path = os.path.dirname(os.path.abspath(__file__))
if project_path not in sys.path:
    sys.path.append(project_path)

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'FootFront.settings')
django.setup()

from django.core import mail
from django.conf import settings

# Force LocMem backend
settings.EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'

from utils.emails import send_order_confirmation_email, send_shipment_update_email
from cart.models import Order, Shipment

def test_emails():
    print("Starting Email Verification...")
    
    # Get a real order and shipment for context
    order = Order.objects.first()
    shipment = Shipment.objects.first()
    
    if not order:
        print("No orders found to test with.")
        return

    # Test Order Confirmation
    print(f"Testing Order Confirmation Email for Order #{order.id}...")
    success_order = send_order_confirmation_email(order)
    
    outbox = mail.outbox
    if success_order and len(outbox) > 0:
        print(f"SUCCESS: Order Confirmation Email 'sent' to {outbox[0].to}")
        print(f"Subject: {outbox[0].subject}")
    else:
        print(f"FAILED: Order Confirmation Email not sent. Success: {success_order}, Outbox size: {len(outbox)}")

    # Test Shipment Update
    if shipment:
        print(f"Testing Shipment Update Email for Shipment #{shipment.id}...")
        success_shipment = send_shipment_update_email(shipment)
        
        # mail.outbox is live
        if success_shipment and len(mail.outbox) > 1:
            print(f"SUCCESS: Shipment Update Email 'sent' to {mail.outbox[1].to}")
            print(f"Subject: {mail.outbox[1].subject}")
        else:
             print(f"FAILED: Shipment Update Email not sent. Success: {success_shipment}, Outbox size: {len(mail.outbox)}")
    else:
        print("No shipments found to test with.")

if __name__ == "__main__":
    test_emails()
