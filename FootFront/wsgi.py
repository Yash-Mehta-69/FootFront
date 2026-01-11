"""
WSGI config for FootFront project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/wsgi/
"""

import os
import dotenv

dotenv.load_dotenv()

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'FootFront.settings')

try:
    application = get_wsgi_application()
    app = application
except Exception as e:
    import traceback
    traceback.print_exc()
    # Create a dummy WSGI app that prints the error
    def application(environ, start_response):
        # Print to console for local debugging
        print(f"WSGI Startup Error: {e}")
        traceback.print_exc()
        
        status = '500 Internal Server Error'
        error_msg = f"Startup Error: {str(e)}\n\n{traceback.format_exc()}"
        response_headers = [('Content-type', 'text/plain')]
        start_response(status, response_headers)
        return [error_msg.encode('utf-8')]
    app = application
