from utils import panel_messages

def panel_messages_processor(request):
    """
    Context processor to add admin_messages and vendor_messages to the context.
    Reading these will clear them from the session.
    """
    # Only fetch if we are in admin or vendor paths to minimize session writes on other pages?
    # Actually, the get_messages function clears the messages. 
    # If we run this on every request, we might clear messages intended for a redirect if we don't display them?
    # But usually, context processors run when rendering a template.
    # If a view redirects, it doesn't render a template, so this won't run.
    # So it is safe to just return them.
    
    return {
        'admin_messages': panel_messages.get_admin_messages(request),
        'vendor_messages': panel_messages.get_vendor_messages(request),
    }
