import json
import re

def parse_auth_error(error):
    """
    Parses an exception or error string (which might be a raw JSON response from Firebase)
    and returns a user-friendly error message.
    """
    error_str = str(error)
    
    # Try to extract JSON from the error string if it's wrapped in other text
    # Often requests lib returns: "400 Client Error: ... for url: ... {json}"
    # or Firebase SDK raises exceptions with the JSON response in the message.
    
    # Pattern to find JSON-like structure: starts with { and ends with }
    # This is a bit naive but works for the specific case mentioned by the user.
    try:
        # Check if the error string itself is valid JSON
        error_json = json.loads(error_str)
    except json.JSONDecodeError:
        # Try to find a JSON substring
        match = re.search(r'(\{.*\})', error_str)
        if match:
            try:
                error_json = json.loads(match.group(1))
            except json.JSONDecodeError:
                error_json = None
        else:
            error_json = None

    if error_json:
        # Navigate the JSON structure (Firebase REST API format)
        # Structure: {"error": {"code": 400, "message": "INVALID_LOGIN_CREDENTIALS", ...}}
        api_error = error_json.get('error', {})
        if isinstance(api_error, dict):
            message_code = api_error.get('message', '')
        else:
            # Sometime it might be just the error dict itself if not nested
            message_code = error_json.get('message', '')

        # Map codes to user-friendly messages
        if 'INVALID_LOGIN_CREDENTIALS' in message_code or 'INVALID_PASSWORD' in message_code or 'EMAIL_NOT_FOUND' in message_code:
            return "Invalid email or password. Please try again."
        elif 'USER_DISABLED' in message_code:
            return "This account has been disabled. Please contact support."
        elif 'TOO_MANY_ATTEMPTS_TRY_LATER' in message_code:
            return "Too many failed attempts. Please try again later."
        elif 'EMAIL_EXISTS' in message_code:
            return "An account with this email already exists."
        elif 'WEAK_PASSWORD' in message_code:
            return "The password is too weak."
        elif 'INVALID_ID_TOKEN' in message_code:
            return "Your session is invalid. Please refresh the page and try again."
        
        # If we successfully parsed JSON but found no known code, 
        # return the raw message code if reasonable, or a generic one.
        if message_code:
            return f"Error: {message_code.replace('_', ' ').title()}"

    # Fallback for simple string matches if JSON parsing failed
    if 'INVALID_LOGIN_CREDENTIALS' in error_str:
        return "Invalid email or password."
    if 'email not found' in error_str.lower():
        return "No account found with this email."
    
    # Generic Fallback
    # Limit length of error shown to user so they don't see huge stack traces
    if len(error_str) > 100:
        return "An unexpected system error occurred."
    
    return error_str
