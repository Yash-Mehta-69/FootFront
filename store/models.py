from django.db import models
from django.utils.text import slugify
from django.core.validators import MinValueValidator, MaxValueValidator
 
# Create your models here.
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager


# Abstract Soft Delete
class SoftDeleteModel(models.Model):
    is_deleted = models.BooleanField(default=False)

    class Meta:
        abstract = True

        
class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', 'admin')

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(email, password, **extra_fields)

# --- Custom User Model ---
class User(AbstractBaseUser, PermissionsMixin):
    ROLE_CHOICES = (
        ('admin', 'admin'),
        ('vendor', 'vendor'),
        ('user', 'user'),
    )
    
    # Standard Django ID is used as Primary Key now
    email = models.EmailField(max_length=75, unique=True) # Used for login 
    first_name = models.CharField(max_length=75)
    last_name = models.CharField(max_length=75)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)
    
    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    def __str__(self):
        return self.email

# --- Customer Model ---
class Customer(models.Model):
    # Foreign Key references user table 
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='customer_profile') 
    phone = models.CharField(max_length=13, unique=True)
    firebase_uid = models.CharField(max_length=128, unique=True, null=True, blank=True)
    is_blocked = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Customer: {self.user.email}"
    

class ShippingAddress(SoftDeleteModel):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    address_line1 = models.CharField(max_length=75)
    address_line2 = models.CharField(max_length=75)
    city = models.CharField(max_length=30)
    state = models.CharField(max_length=30)
    postal_code = models.CharField(max_length=10)

    def __str__(self):
        return f"{self.city}, {self.state}"
    
class Category(SoftDeleteModel):
    name = models.CharField(max_length=100, unique=True)
    parent_category = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children')
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(max_length=255, blank=True)
    cat_image = models.ImageField(upload_to='categories', blank=True)

    class Meta:
        verbose_name = 'category'
        verbose_name_plural = 'categories'

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug and self.name:
            self.slug = slugify(self.name)
        super(Category, self).save(*args, **kwargs)


class Color(models.Model):
    name = models.CharField(max_length=50, unique=True)
    hex_code = models.CharField(max_length=7)

    def __str__(self):
        return self.name

class Size(models.Model):
    size_label = models.CharField(max_length=20, unique=True)

    def __str__(self):
        return self.size_label

class Product(SoftDeleteModel):
    GENDER_CHOICES = (
        ('M', 'Men'),
        ('W', 'Women'),
        ('U', 'Unisex'),
    )
    name = models.CharField(max_length=150)
    slug = models.SlugField(max_length=150, unique=True)
    description = models.TextField(max_length=500, blank=True)
    vendor = models.ForeignKey('vendor.Vendor', on_delete=models.CASCADE)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, default='U')
    product_image = models.ImageField(upload_to='photos/products', blank=True, null=True)
    is_trending = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_date = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.slug and self.name:
            self.slug = slugify(self.name)
        super(Product, self).save(*args, **kwargs)

class ProductVariant(SoftDeleteModel):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    size = models.ForeignKey(Size, on_delete=models.PROTECT)
    color = models.ForeignKey(Color, on_delete=models.PROTECT)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.IntegerField()
    image = models.ImageField(upload_to='photos/products')

    def __str__(self):
        return f"{self.product.name} - {self.size} - {self.color}"

class AttributeRequest(models.Model):
    REQUEST_TYPES = (
        ('Category', 'Category'),
        ('Size', 'Size'),
        ('Color', 'Color'),
    )
    STATUS_CHOICES = (
        ('Pending', 'Pending'),
        ('Approved', 'Approved'),
        ('Rejected', 'Rejected'),
    )
    vendor = models.ForeignKey('vendor.Vendor', on_delete=models.CASCADE)
    attribute_type = models.CharField(max_length=20, choices=REQUEST_TYPES)
    attribute_value = models.CharField(max_length=100)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.attribute_type}: {self.attribute_value} - {self.vendor}"
    
class Review(SoftDeleteModel):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.comment
    
class Complaint(SoftDeleteModel):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, null=True, blank=True)
    subject = models.CharField(max_length=200)
    complaint_text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Complaint: {self.subject} by {self.customer.user.email}"