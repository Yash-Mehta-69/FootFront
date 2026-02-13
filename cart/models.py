from django.db import models
from store.models import User, Product, Customer, ProductVariant, SoftDeleteModel, ShippingAddress
from vendor.models import Vendor

# Create your models here.

class Cart(SoftDeleteModel):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Cart for {self.customer.user.email}"

    def get_total_price(self):
        return sum(item.sub_total for item in self.items.filter(is_deleted=False))

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

    @property
    def admin_earnings(self):
        from decimal import Decimal
        return self.total_amount * Decimal('0.07')

    @property
    def get_items_display(self):
        items = self.items.all()
        return ", ".join([f"{item.quantity}x {item.product_variant.product.name} ({item.product_variant.size.size_label}/{item.product_variant.color.name})" for item in items])

    @property
    def payment_info(self):
        if hasattr(self, 'payment'):
            p = self.payment
            return f"{p.get_status_display()} ({p.get_payment_method_display()}) - ID: {p.razorpay_payment_id}"
        return "Not Paid"

    def __str__(self):
        return f"Order #{self.pk} by {self.customer.user.email}"

class OrderItem(SoftDeleteModel):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product_variant = models.ForeignKey(ProductVariant, on_delete=models.PROTECT)
    quantity = models.IntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)

    @property
    def total_price(self):
        return self.price * self.quantity

    def __str__(self):
        return f"{self.quantity} x {self.product_variant.product.name} in Order #{self.order.pk}"

class Shipment(SoftDeleteModel):
    STATUS_CHOICES = (
        ('preparing', 'Preparing'),
        ('shipped', 'Shipped'),
        ('in_transit', 'In Transit'),
        ('delivered', 'Delivered'),
    )
    order_item = models.OneToOneField(OrderItem, on_delete=models.CASCADE, related_name='shipment')
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE)
    tracking_number = models.CharField(max_length=100, blank=True)
    courier_name = models.CharField(max_length=100, blank=True)
    shipped_at = models.DateTimeField(null=True, blank=True)
    expected_delivery = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='preparing')

    def __str__(self):
        return f"Shipment for OrderItem #{self.order_item.pk}"

class ShipmentStatusHistory(SoftDeleteModel):
    shipment = models.ForeignKey(Shipment, on_delete=models.CASCADE, related_name='history')
    status = models.CharField(max_length=50)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.status} for Shipment #{self.shipment.pk}"

class Payment(SoftDeleteModel):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    )
    METHOD_CHOICES = (
        ('card', 'Card'),
        ('upi', 'UPI'),
        ('netbanking', 'Netbanking'),
        ('wallet', 'Wallet'),
        ('emi', 'EMI'),
    )
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='payment')
    payment_date = models.DateTimeField(auto_now_add=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=50, choices=METHOD_CHOICES)
    razorpay_order_id = models.CharField(max_length=100, blank=True)
    razorpay_payment_id = models.CharField(max_length=100, blank=True)
    razorpay_signature = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    def __str__(self):
        return f"Payment for Order #{self.order.pk}"

class TransferLog(SoftDeleteModel):
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='transfers', null=True)
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name='transfers', null=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_id = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, default='success')

    def __str__(self):
        return f"Transfer of {self.amount} to {self.vendor.shopName}"
