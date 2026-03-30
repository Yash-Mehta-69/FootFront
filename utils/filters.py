from django.utils import timezone
from datetime import timedelta, datetime

def get_date_range(filter_type, start_date_str=None, end_date_str=None):
    """
    Returns (start_date, end_date) for the given filter type.
    """
    now = timezone.now()
    
    if filter_type == 'today':
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        return start_date, None
        
    elif filter_type == 'this_week':
        # Start of the current week (Assuming Monday as start of week)
        start_date = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
        return start_date, None
        
    elif filter_type == 'this_month':
        # First day of the current month
        start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        return start_date, None
        
    elif filter_type == 'custom' and start_date_str and end_date_str:
        try:
            # Parse from HTML date input format (YYYY-MM-DD)
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
            
            # Make timezone aware
            if timezone.is_naive(start_date):
                start_date = timezone.make_aware(start_date)
            if timezone.is_naive(end_date):
                end_date = timezone.make_aware(end_date)
            
            # Adjust range: start at 00:00:00 and end at 23:59:59
            start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = end_date.replace(hour=23, minute=59, second=59, microsecond=999999)
            
            return start_date, end_date
        except (ValueError, TypeError):
            return None, None
            
    return None, None
