import os
import sys
import django
from django.conf import settings
from django.contrib.sessions.middleware import SessionMiddleware

# Setup Django environment
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'FootFront.settings')
django.setup()

from django.test import RequestFactory
from utils import panel_messages

def test_panel_messages():
    print("Testing panel_messages utility...")
    
    # Create request with session
    factory = RequestFactory()
    request = factory.get('/')
    middleware = SessionMiddleware(lambda x: None)
    middleware.process_request(request)
    request.session.save()
    
    # Test Admin Messages
    print("1. Adding Admin Message...")
    panel_messages.add_admin_message(request, 'success', 'Admin Test Message')
    
    # Check session directly (should exist)
    if 'admin_messages' in request.session:
        print("   Success: admin_messages found in session.")
        print(f"   Value: {request.session['admin_messages']}")
    else:
        print("   FAILURE: admin_messages NOT found in session.")
        
    # Retrieve messages (should consume them)
    print("2. Retrieving Admin Messages...")
    msgs = panel_messages.get_admin_messages(request)
    print(f"   Retrieved: {msgs}")
    
    if len(msgs) == 1 and msgs[0]['message'] == 'Admin Test Message':
        print("   Success: Message content correct.")
    else:
        print("   FAILURE: Message content incorrect.")
        
    # Check session again (should be empty/gone)
    if not request.session.get('admin_messages'):
        print("   Success: admin_messages cleared from session.")
    else:
        print("   FAILURE: admin_messages NOT cleared from session.")

    # Test Vendor Messages
    print("3. Adding Vendor Message...")
    panel_messages.add_vendor_message(request, 'warning', 'Vendor Test Message')
    
    msgs = panel_messages.get_vendor_messages(request)
    if len(msgs) == 1 and msgs[0]['message'] == 'Vendor Test Message' and msgs[0]['level'] == 'warning':
        print("   Success: Vendor message retrieved correctly.")
    else:
        print("   FAILURE: Vendor message incorrect.")

if __name__ == "__main__":
    test_panel_messages()
