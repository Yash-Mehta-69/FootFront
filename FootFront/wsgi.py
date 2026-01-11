"""
WSGI config for FootFront project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'FootFront.settings')

application = get_wsgi_application()
app = application

# Serverless cold-start DB init
if 'VERCEL' in os.environ: # Only run on Vercel
    try:
        from django.core.management import call_command
        # SQLite in /tmp is ephemeral, so we need to init it if it's missing (which is always on cold start)
        # Note: settings.py is already configured to use /tmp/db.sqlite3 on Vercel
        print("Running migrations...")
        call_command('migrate', interactive=False)
        
        # Try multiple potential locations
        possible_paths = [
            os.path.join(os.path.dirname(os.path.dirname(__file__)), 'initial_data.json'),
            os.path.join(os.getcwd(), 'initial_data.json'),
            'initial_data.json'
        ]
        
        fixture_path = None
        for path in possible_paths:
            if os.path.exists(path):
                fixture_path = path
                break
                
        print(f"Searched paths: {possible_paths}")
        print(f"Found at: {fixture_path}")

        if os.path.exists(fixture_path):
            print(f"Loading data from {fixture_path}...")
            call_command('loaddata', fixture_path)
            print("Data loaded.")
        else:
            print("Fixture file NOT FOUND!")
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Error during Vercel DB init: {e}")
