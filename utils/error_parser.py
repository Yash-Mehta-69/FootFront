import json

def parse_firebase_error(error_input):
    """
    Parses Firebase error input (could be a raw string, a JSON string, or a dict)
    into a user-friendly message.
    """
    error_message = str(error_input)
    
    # Try to parse if it's a JSON string
    try:
        if isinstance(error_input, str) and (error_input.strip().startswith('{') or error_input.strip().startswith('[')):
            data = json.loads(error_input)
            if isinstance(data, dict):
                # Check for standard Firebase error structure
                if 'error' in data and isinstance(data['error'], dict):
                    error_message = data['error'].get('message', error_message)
                elif 'message' in data:
                    error_message = data['message']
    except (ValueError, TypeError, json.JSONDecodeError):
        pass

    # Map internal codes to user-friendly messages
    mapping = {
        "EMAIL_NOT_FOUND": "This email address is not registered in our system.",
        "INVALID_PASSWORD": "The password you entered is incorrect.",
        "USER_DISABLED": "This account has been disabled. Please contact support.",
        "EMAIL_EXISTS": "An account with this email address already exists.",
        "OPERATION_NOT_ALLOWED": "Authentication protocol error. Contact support.",
        "TOO_MANY_ATTEMPTS_EXCEEDED": "Too many failed attempts. Please try again later.",
        "INVALID_EMAIL": "The email address provided is invalid.",
        "WEAK_PASSWORD": "The password provided is too weak.",
        "USER_NOT_FOUND": "No user identity found with these credentials.",
        "INVALID_LOGIN_CREDENTIALS": "Invalid login credentials. Please check your email and password.",
    }

    # Clean up the error message (e.g., "INVALID_PASSWORD : ..." -> "INVALID_PASSWORD")
    clean_error = error_message.split(' : ')[0].split('] ')[-1].strip()
    
    # Return mapped message or the original (cleaned) message
    return mapping.get(clean_error, error_message)
