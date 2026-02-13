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
    elif filter_type == 'weekly':
        start_date = now - timedelta(days=7)
        return start_date, None
    elif filter_type == 'yearly':
        start_date = now - timedelta(days=365)
        return start_date, None
    elif filter_type == 'custom' and start_date_str and end_date_str:
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
            
            # Make timezone aware
            if timezone.is_naive(start_date):
                start_date = timezone.make_aware(start_date)
            if timezone.is_naive(end_date):
                end_date = timezone.make_aware(end_date)
                
            # Set end_date to end of day
            end_date = end_date.replace(hour=23, minute=59, second=59, microsecond=999999)
            return start_date, end_date
        except ValueError:
            return None, None
    return None, None
