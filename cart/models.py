from django.db import models
from store.models import User, Product, Customer, ProductVariant, SoftDeleteModel, ShippingAddress
from vendor.models import Vendor

# Create your models here.

class Cart(SoftDeleteModel):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Cart for {self.customer.user.email}"

class CartItem(SoftDeleteModel):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product_variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.quantity} x {self.product_variant.product.name} ({self.product_variant.size}, {self.product_variant.color})"

    @property
    def sub_total(self):
        return self.product_variant.price * self.quantity

class Wishlist(SoftDeleteModel):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    product_variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE)
    added_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Wishlist item: {self.product_variant.product.name} for {self.customer.user.email}"

class Order(SoftDeleteModel):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    order_date = models.DateTimeField(auto_now_add=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    shipping_address = models.ForeignKey(ShippingAddress, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return f"Order #{self.pk} by {self.customer.user.email}"

class OrderItem(SoftDeleteModel):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product_variant = models.ForeignKey(ProductVariant, on_delete=models.PROTECT)
    quantity = models.IntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.quantity} x {self.product_variant.product.name} in Order #{self.order.pk}"

class Shipment(SoftDeleteModel):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
        ('returned', 'Returned'),
    )
    order_item = models.OneToOneField(OrderItem, on_delete=models.CASCADE, related_name='shipment')
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE)
    tracking_number = models.CharField(max_length=100)
    courier_name = models.CharField(max_length=100)
    shipped_at = models.DateTimeField(auto_now_add=True)
    expected_delivery = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    def __str__(self):
        return f"Shipment for {self.order_item}"

class Payment(SoftDeleteModel):
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='payment')
    payment_date = models.DateTimeField(auto_now_add=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=50, default='Razorpay')
    razorpay_order_id = models.CharField(max_length=100, blank=True)
    razorpay_payment_id = models.CharField(max_length=100, blank=True)
    razorpay_signature = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=20, default='pending')

    def __str__(self):
        return f"Payment for Order #{self.order.pk}"

class TransferLog(SoftDeleteModel):
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_id = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, default='success')

    def __str__(self):
        return f"Transfer of {self.amount} to {self.vendor.shopName}"
