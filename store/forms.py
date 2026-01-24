from django import forms
from .models import Complaint, Product, Category, Size, Color
from django.core.validators import RegexValidator
class ComplaintForm(forms.ModelForm):
    class Meta:
        model = Complaint
        fields = ['subject', 'product', 'complaint_text']
        widgets = {
            'subject': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Subject of your issue',
                'required': 'required',
                'minlength': '5'
            }),
            'complaint_text': forms.Textarea(attrs={
                'class': 'form-control', 
                'placeholder': 'Describe your issue in detail...', 
                'rows': 5,
                'required': 'required',
                'minlength': '20'
            }),
            'product': forms.Select(attrs={
                'class': 'form-control',
            }),
        }

    def __init__(self, *args, **kwargs):
        super(ComplaintForm, self).__init__(*args, **kwargs)
        # Filter products to only those not deleted, if needed
        self.fields['product'].queryset = Product.objects.filter(is_deleted=False)
        self.fields['product'].empty_label = "General Inquiry (No specific product)"

from .models import Review
class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ['rating', 'comment']
        widgets = {
            'rating': forms.NumberInput(attrs={'min': 1, 'max': 5, 'type': 'hidden', 'required': 'required'}),
            'comment': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Share your thoughts about the product...', 'required': 'required', 'minlength': '10'}),
        }

from .models import User, Customer, ShippingAddress

class UserUpdateForm(forms.ModelForm):
    phone = forms.CharField(max_length=10, required=True, validators=[
        RegexValidator(r'^\d{10}$', "Phone number must be exactly 10 digits.")
    ], widget=forms.TextInput(attrs={
        'class': 'form-control',
        'placeholder': 'Phone Number',
    }))

    class Meta:
        model = User
        fields = ['first_name', 'last_name']
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'First Name',
                'required': 'required',
                'data-pattern': '^[a-zA-Z\\s]+$',
                'data-error': 'Letters only'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Last Name',
                'required': 'required',
                'data-pattern': '^[a-zA-Z\\s]+$',
                'data-error': 'Letters only'
            }),
        }

class ShippingAddressForm(forms.ModelForm):
    class Meta:
        model = ShippingAddress
        fields = ['address_line1', 'address_line2', 'city', 'state', 'postal_code']
        widgets = {
            'address_line1': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Address Line 1', 'required': 'required'}),
            'address_line2': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Address Line 2 (Optional)'}),
            'city': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'City', 'required': 'required', 'data-pattern': '^[a-zA-Z\\s]+$'}),
            'state': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'State', 'required': 'required', 'data-pattern': '^[a-zA-Z\\s]+$'}),
            'postal_code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Postal Code', 'required': 'required', 'data-pattern': '^\\d{6}$', 'data-error': '6-digit PIN code'}),
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
                'required': 'required',
                'data-pattern': '^[a-zA-Z\\s\\-&]+$',
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
            
            if name.isdigit():
                raise forms.ValidationError("Category name cannot be purely numeric. Please include at least one letter.")
            
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
            'name': forms.TextInput(attrs={
                'class': 'form-control-custom', 
                'placeholder': 'Enter product name', 
                'required': 'required',
            }),
            'description': forms.Textarea(attrs={'class': 'form-control-custom', 'rows': 4, 'placeholder': 'Enter product description', 'required': 'required'}),
            'vendor': forms.Select(attrs={'class': 'form-select-custom', 'required': 'required'}),
            'category': forms.Select(attrs={'class': 'form-select-custom', 'required': 'required'}),
            'gender': forms.Select(attrs={'class': 'form-select-custom', 'required': 'required'}),
            'product_image': forms.ClearableFileInput(attrs={'class': 'form-control-custom', 'style': 'padding: 7px;'}), # Note: image may be required only on Add, handled in view or client
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
            'size_label': forms.TextInput(attrs={'class': 'form-control-custom', 'placeholder': 'Enter Size Label', 'required': 'required'}),
        }

class ColorForm(forms.ModelForm):
    class Meta:
        model = Color
        fields = ['name', 'hex_code']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control-custom', 'placeholder': 'Color Name', 'required': 'required'}),
            'hex_code': forms.TextInput(attrs={'class': 'form-control-custom', 'type': 'color', 'style': 'height: 40px; width: 60px; padding: 2px;', 'required': 'required'}),
        }

class CustomerAdminForm(forms.Form):
    first_name = forms.CharField(max_length=150, required=True, validators=[
        RegexValidator(r'^[a-zA-Z\s]+$', "First name must contain only letters.")
    ], widget=forms.TextInput(attrs={'class': 'form-control-custom', 'placeholder': 'e.g. John'}))
    
    last_name = forms.CharField(max_length=150, required=True, validators=[
        RegexValidator(r'^[a-zA-Z\s]+$', "Last name must contain only letters.")
    ], widget=forms.TextInput(attrs={'class': 'form-control-custom', 'placeholder': 'e.g. Doe'}))
    
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={'class': 'form-control-custom', 'placeholder': 'name@example.com'}))
    
    phone = forms.CharField(max_length=10, required=True, validators=[
        RegexValidator(r'^\d{10}$', "Phone number must be exactly 10 digits.")
    ], widget=forms.TextInput(attrs={'class': 'form-control-custom', 'placeholder': 'e.g. 9876543210'}))
    
    status = forms.ChoiceField(choices=[('Active', 'Active'), ('Blocked', 'Blocked')], widget=forms.Select(attrs={'class': 'form-select-custom'}))
    
    # Password fields only for "Add" action
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control-custom'}), required=False, min_length=6)
    confirm_password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control-custom'}), required=False)

    def __init__(self, *args, **kwargs):
        self.instance_user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if self.instance_user:
            self.fields['password'].required = False
            self.fields['confirm_password'].required = False

    def clean_email(self):
        email = self.cleaned_data.get('email')
        qs = User.objects.filter(email=email)
        if self.instance_user:
            qs = qs.exclude(pk=self.instance_user.pk)
        if qs.exists():
            raise forms.ValidationError("Email is already registered.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password and confirm_password and password != confirm_password:
            self.add_error('confirm_password', "Passwords do not match.")
        return cleaned_data

class VendorAdminForm(CustomerAdminForm):
    shopName = forms.CharField(max_length=30, required=True, widget=forms.TextInput(attrs={'class': 'form-control-custom', 'placeholder': 'Enter shop name'}))
    business_phone = forms.CharField(max_length=10, required=True, validators=[
        RegexValidator(r'^\d{10}$', "Phone number must be exactly 10 digits.")
    ], widget=forms.TextInput(attrs={'class': 'form-control-custom', 'placeholder': '10-digit number'}))
    shopAddress = forms.CharField(widget=forms.Textarea(attrs={'class': 'form-control-custom', 'rows': 2, 'placeholder': 'Full address'}))
    description = forms.CharField(widget=forms.Textarea(attrs={'class': 'form-control-custom', 'rows': 3, 'placeholder': 'Shop description'}), required=False)
    
    profile_picture = forms.ImageField(required=False, widget=forms.ClearableFileInput(attrs={'class': 'form-control-custom', 'style': 'padding: 7px;'}))
    panCard = forms.ImageField(required=False, widget=forms.ClearableFileInput(attrs={'class': 'form-control-custom', 'style': 'padding: 7px;'}))
    adharCard = forms.ImageField(required=False, widget=forms.ClearableFileInput(attrs={'class': 'form-control-custom', 'style': 'padding: 7px;'}))
    
    bank_name = forms.CharField(required=True, widget=forms.TextInput(attrs={'class': 'form-control-custom', 'placeholder': 'Bank Name'}))
    account_number = forms.CharField(required=True, widget=forms.TextInput(attrs={'class': 'form-control-custom', 'placeholder': 'Account Number'}))
    ifsc_code = forms.CharField(max_length=11, required=True, validators=[
        RegexValidator(r'^[A-Z]{4}0[A-Z0-9]{6}$', "Invalid IFSC Code (e.g. SBIN0123456)")
    ], widget=forms.TextInput(attrs={'class': 'form-control-custom', 'placeholder': 'IFSC Code'}))
    beneficiary_name = forms.CharField(required=True, widget=forms.TextInput(attrs={'class': 'form-control-custom', 'placeholder': 'Beneficiary Name'}))

    def __init__(self, *args, **kwargs):
        self.vendor_instance = kwargs.pop('vendor', None)
        super().__init__(*args, **kwargs)
        if not self.vendor_instance:
            self.fields['profile_picture'].required = True
            self.fields['panCard'].required = True
            self.fields['adharCard'].required = True

    def clean_shopName(self):
        shopName = self.cleaned_data.get('shopName')
        qs = Vendor.objects.filter(shopName=shopName)
        if self.vendor_instance:
            qs = qs.exclude(pk=self.vendor_instance.pk)
        if qs.exists():
            raise forms.ValidationError("Shop name is already taken.")
        return shopName

