
import os
import sys
import django

# Mock Vercel env
os.environ['VERCEL'] = '1'
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'FootFront.settings')

# Setup Django
django.setup()

# Import WSGI to trigger init logic
# We need to manually trigger the code in wsgi.py since importing it might not run the if block if it's inside 'application' scope (it's not, it's global).
# Wait, the code in wsgi.py is at module level? Yes.
import FootFront.wsgi
