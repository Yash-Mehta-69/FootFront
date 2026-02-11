import csv
import datetime
from django.http import HttpResponse
from django.utils import timezone
from django.db import models

def export_to_csv(queryset, filename_prefix, fields):
    """
    Generic function to export a queryset to CSV.
    fields: List of tuples (field_name, verbose_name) or just strings.
    If tuple, first element can be a property or related field path (e.g. 'user.email').
    """
    response = HttpResponse(content_type='text/csv')
    timestamp = timezone.now().strftime('%Y-%m-%d_%H%M%S')
    response['Content-Disposition'] = f'attachment; filename="{filename_prefix}_{timestamp}.csv"'

    writer = csv.writer(response)
    
    # Headers
    headers = []
    for field in fields:
        if isinstance(field, tuple):
            headers.append(field[1])
        else:
            headers.append(field.replace('_', ' ').title())
    writer.writerow(headers)

    # Data rows
    for obj in queryset:
        row = []
        for field in fields:
            field_name = field[0] if isinstance(field, tuple) else field
            
            # Handle nested fields (e.g., 'user.email')
            val = obj
            for part in field_name.split('.'):
                if val is None:
                    break
                # Check for callable (method)
                attr = getattr(val, part, None)
                if callable(attr) and not isinstance(attr, models.Model): # basic check to avoid executing models
                    try:
                        val = attr()
                    except:
                        val = attr
                else:
                    val = attr
            
            if val is None:
                val = ""
            elif isinstance(val, (datetime.datetime, datetime.date)):
                val = val.strftime('%Y-%m-%d %H:%M')
            
            row.append(val)
        writer.writerow(row)

    return response
