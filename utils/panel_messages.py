from django.conf import settings

# Keys for session storage
ADMIN_MESSAGES_SESSION_KEY = 'admin_messages'
VENDOR_MESSAGES_SESSION_KEY = 'vendor_messages'

def add_message(request, session_key, level, message):
    """
    Add a message to the specified session key.
    Level can be 'success', 'error', 'warning', 'info'.
    """
    messages = request.session.get(session_key, [])
    messages.append({'level': level, 'message': message})
    request.session[session_key] = messages
    request.session.modified = True

def get_messages(request, session_key):
    """
    Retrieve and clear messages from the specified session key.
    """
    messages = request.session.get(session_key, [])
    if messages:
        request.session[session_key] = []
        request.session.modified = True
    return messages

# --- Admin Helpers ---

def add_admin_message(request, level, message):
    add_message(request, ADMIN_MESSAGES_SESSION_KEY, level, message)

def get_admin_messages(request):
    return get_messages(request, ADMIN_MESSAGES_SESSION_KEY)

# --- Vendor Helpers ---

def add_vendor_message(request, level, message):
    add_message(request, VENDOR_MESSAGES_SESSION_KEY, level, message)

def get_vendor_messages(request):
    return get_messages(request, VENDOR_MESSAGES_SESSION_KEY)
