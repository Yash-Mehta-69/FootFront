from django.urls import path
from . import views

urlpatterns = [
    path("vendordashboard/",views.vendor_dashboard,name='vendordashboard'),
    path("products/",views.vendor_products,name='vendor_products'),
    path("orders/",views.vendor_orders,name='vendor_orders'),
    path("add-product/",views.add_product,name='add_product'),
    path("edit-product/",views.edit_product,name='vendor_edit_product'),
    path("product-detail/",views.product_detail,name='vendor_product_detail'),
    path("categories/",views.vendor_categories,name='vendor_categories'),
    path("shipments/",views.vendor_shipments,name='vendor_shipments'),
    path("shipments/update/<int:pk>/",views.update_shipment_status,name='update_shipment_status'),
    path("shipments/create/<int:order_item_id>/",views.create_shipment,name='create_shipment'),
    path("profile/",views.vendor_profile,name='vendor_profile'),
    path("analytics/",views.vendor_analytics,name='vendor_analytics'),
    path("help/",views.vendor_help,name='vendor_help'),
]
