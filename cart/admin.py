from django.contrib import admin
from .models import Cart, CartItem, Wishlist, Order, OrderItem, Shipment, Payment, TransferLog

# Register your models here.
admin.site.register(Cart)
admin.site.register(CartItem)
admin.site.register(Wishlist)
admin.site.register(Order)
admin.site.register(OrderItem)
admin.site.register(Shipment)
admin.site.register(Payment)
admin.site.register(TransferLog)
