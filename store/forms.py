from django import forms
from .models import Complaint, Product, Category, Size, Color

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


from .models import Category

class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'parent_category', 'description', 'cat_image']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control-custom',
                'placeholder': 'Category Name',
            }),
            'parent_category': forms.Select(attrs={
                'class': 'form-select-custom',
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control-custom',
                'placeholder': 'Description...',
                'rows': 4,
            }),
            'cat_image': forms.ClearableFileInput(attrs={
                'class': 'form-control-custom',
                'style': 'padding: 7px;'
            }),
        }

    def __init__(self, *args, **kwargs):
        super(CategoryForm, self).__init__(*args, **kwargs)
        self.fields['parent_category'].queryset = Category.objects.filter(is_deleted=False)
        self.fields['parent_category'].empty_label = "No Parent (Top Level)"

    def clean_name(self):
        name = self.cleaned_data.get('name')
        if name:
            import re
            if not re.match(r'^[a-zA-Z0-9\s\-\&]+$', name):
                raise forms.ValidationError("Category name can only contain letters, numbers, spaces, hyphens, and '&'.")
            
            # Case-insensitive unique check
            # Exclude current instance if editing
            qs = Category.objects.filter(name__iexact=name, is_deleted=False)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError("A category with this name already exists.")
        return name

    def clean_parent_category(self):
        parent = self.cleaned_data.get('parent_category')
        if parent and self.instance.pk and parent.pk == self.instance.pk:
            raise forms.ValidationError("A category cannot be its own parent.")
        return parent


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['name', 'description', 'vendor', 'category', 'gender', 'product_image', 'is_trending']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control-custom', 'placeholder': 'Enter product name'}),
            'description': forms.Textarea(attrs={'class': 'form-control-custom', 'rows': 4, 'placeholder': 'Enter product description'}),
            'vendor': forms.Select(attrs={'class': 'form-select-custom'}),
            'category': forms.Select(attrs={'class': 'form-select-custom'}),
            'gender': forms.Select(attrs={'class': 'form-select-custom'}),
            'product_image': forms.ClearableFileInput(attrs={'class': 'form-control-custom', 'style': 'padding: 7px;'}),
            'is_trending': forms.CheckboxInput(attrs={'class': 'form-check-input', 'id': 'isTrending'}),
        }

    def __init__(self, *args, **kwargs):
        super(ProductForm, self).__init__(*args, **kwargs)
        self.fields['category'].queryset = Category.objects.filter(is_deleted=False)
        # Vendor field might be hidden/disabled for Vendor panel, but handled in init or view

class VendorProductForm(ProductForm):
    class Meta(ProductForm.Meta):
        exclude = ['vendor']

class SizeForm(forms.ModelForm):
    class Meta:
        model = Size
        fields = ['size_label']
        widgets = {
            'size_label': forms.TextInput(attrs={'class': 'form-control form-control-custom', 'placeholder': 'Enter Size Label'}),
        }

class ColorForm(forms.ModelForm):
    class Meta:
        model = Color
        fields = ['name', 'hex_code']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control form-control-custom', 'placeholder': 'Color Name'}),
            'hex_code': forms.TextInput(attrs={'class': 'form-control form-control-custom', 'type': 'color', 'style': 'height: 40px; width: 60px; padding: 2px;'}),
        }





