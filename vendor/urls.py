from django.urls import path
from . import views

urlpatterns = [
    path("vendordashboard/",views.vendor_dashboard,name='vendordashboard'),
    path("products/",views.vendor_products,name='vendor_products'),
    path("orders/",views.vendor_orders,name='vendor_orders'),
    path("add-product/",views.add_product,name='add_product'),
    path("edit-product/",views.edit_product,name='vendor_edit_product'),
    path("product-detail/",views.product_detail,name='vendor_product_detail'),
]
