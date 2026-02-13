import csv
import datetime
from django.http import HttpResponse
from django.utils import timezone
from django.db import models
from django.template.loader import get_template
from xhtml2pdf import pisa
from io import BytesIO

def _get_export_data(queryset, fields):
    """Internal helper to extract data from queryset based on fields."""
    headers = []
    for field in fields:
        if isinstance(field, tuple):
            headers.append(field[1])
        else:
            headers.append(field.replace('_', ' ').title())

    data = []
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
                if callable(attr) and not isinstance(attr, models.Model): 
                    try:
                        val = attr()
                    except:
                        val = attr
                else:
                    val = attr
            
            if val is None:
                val = ""
            elif isinstance(val, bool):
                val = str(val)
            elif isinstance(val, (datetime.datetime, datetime.date)):
                val = val.strftime('%Y-%m-%d %H:%M')
            
            row.append(val)
        data.append(row)
    
    return headers, data

def export_to_csv(queryset, filename_prefix, fields):
    """Generic function to export a queryset to CSV."""
    headers, data = _get_export_data(queryset, fields)
    
    response = HttpResponse(content_type='text/csv')
    timestamp = timezone.now().strftime('%Y-%m-%d_%H%M%S')
    response['Content-Disposition'] = f'attachment; filename="{filename_prefix}_{timestamp}.csv"'

    writer = csv.writer(response)
    writer.writerow(headers)
    for row in data:
        writer.writerow(row)

    return response

def export_to_pdf(queryset, filename_prefix, fields):
    """Generic function to export a queryset to PDF."""
    headers, data = _get_export_data(queryset, fields)
    
    template = get_template('utils/pdf_export.html')
    # Force wrap long strings (like IDs, Emails) to prevent bleeding
    # xhtml2pdf has poor support for CSS word-break, so we inject <br/> tags.
    processed_data = []
    for row in data:
        new_row = []
        for cell in row:
            if isinstance(cell, str) and len(cell) > 12:
                # Split long words (longer than 12 chars)
                words = cell.split(' ')
                new_words = []
                for word in words:
                    if len(word) > 12:
                        # Chunk the word every 12 chars
                        chunks = [word[i:i+12] for i in range(0, len(word), 12)]
                        new_words.append('<br/>'.join(chunks))
                    else:
                        new_words.append(word)
                new_row.append(' '.join(new_words))
            else:
                new_row.append(cell)
        processed_data.append(new_row)

    context = {
        'headers': headers,
        'data': processed_data,
        'title': filename_prefix.replace('_', ' ').title(),
        'timestamp': timezone.now().strftime('%Y-%m-%d %H:%M:%S'),
        'current_year': timezone.now().year,
        'col_width': 98 / len(headers) if headers else 100
    }
    
    html = template.render(context)
    result = BytesIO()
    pdf = pisa.pisaDocument(BytesIO(html.encode("UTF-8")), result)
    
    if not pdf.err:
        response = HttpResponse(result.getvalue(), content_type='application/pdf')
        timestamp = timezone.now().strftime('%Y-%m-%d_%H%M%S')
        response['Content-Disposition'] = f'attachment; filename="{filename_prefix}_{timestamp}.pdf"'
        return response
    
    return HttpResponse("Error generating PDF", status=500)
