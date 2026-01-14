from django import forms
from .models import Complaint, Product

class ComplaintForm(forms.ModelForm):
    class Meta:
        model = Complaint
        fields = ['subject', 'product', 'complaint_text']
        widgets = {
            'subject': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Subject of your issue',
                'style': 'background: var(--input-bg); color: var(--input-text); border: 1px solid var(--input-border);'
            }),
            'complaint_text': forms.Textarea(attrs={
                'class': 'form-control', 
                'placeholder': 'Describe your issue in detail...', 
                'rows': 5,
                'style': 'background: var(--input-bg); color: var(--input-text); border: 1px solid var(--input-border);'
            }),
            'product': forms.Select(attrs={
                'class': 'form-control',
                'style': 'background: var(--input-bg); color: var(--input-text); border: 1px solid var(--input-border);'
            }),
        }

    def __init__(self, *args, **kwargs):
        super(ComplaintForm, self).__init__(*args, **kwargs)
        # Filter products to only those not deleted, if needed
        self.fields['product'].queryset = Product.objects.filter(is_deleted=False)
        self.fields['product'].empty_label = "General Inquiry (No specific product)"

from .models import User, Customer, ShippingAddress

class UserUpdateForm(forms.ModelForm):
    phone = forms.CharField(max_length=13, required=True, widget=forms.TextInput(attrs={
        'class': 'form-control',
        'placeholder': 'Phone Number',
        'style': 'background: var(--input-bg); color: var(--input-text); border: 1px solid var(--input-border);'
    }))

    class Meta:
        model = User
        fields = ['first_name', 'last_name']
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'First Name',
                'style': 'background: var(--input-bg); color: var(--input-text); border: 1px solid var(--input-border);'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Last Name',
                'style': 'background: var(--input-bg); color: var(--input-text); border: 1px solid var(--input-border);'
            }),
        }

class ShippingAddressForm(forms.ModelForm):
    class Meta:
        model = ShippingAddress
        fields = ['address_line1', 'address_line2', 'city', 'state', 'postal_code']
        widgets = {
            'address_line1': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Address Line 1', 'style': 'background: var(--input-bg); color: var(--input-text); border: 1px solid var(--input-border);'}),
            'address_line2': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Address Line 2 (Optional)', 'style': 'background: var(--input-bg); color: var(--input-text); border: 1px solid var(--input-border);'}),
            'city': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'City', 'style': 'background: var(--input-bg); color: var(--input-text); border: 1px solid var(--input-border);'}),
            'state': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'State', 'style': 'background: var(--input-bg); color: var(--input-text); border: 1px solid var(--input-border);'}),
            'postal_code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Postal Code', 'style': 'background: var(--input-bg); color: var(--input-text); border: 1px solid var(--input-border);'}),
        }

