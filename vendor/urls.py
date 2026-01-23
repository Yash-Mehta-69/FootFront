from django.urls import path
from . import views

urlpatterns = [
    path("vendordashboard/",views.vendor_dashboard,name='vendordashboard'),
    path("products/",views.vendor_products,name='vendor_products'),
    path("orders/",views.vendor_orders,name='vendor_orders'),
    path("add-product/",views.add_product,name='vendor_add_product'),
    path("request-attribute/", views.request_attribute, name='vendor_request_attribute'),
    path("edit-product/<int:pk>/",views.edit_product,name='vendor_edit_product'),
    path("products/<int:pk>/",views.vendor_product_detail,name='vendor_product_detail'),
    path("categories/<int:pk>/",views.vendor_category_detail,name='vendor_category_detail'),
    path("shipments/<int:pk>/",views.vendor_shipment_detail,name='vendor_shipment_detail'),
    path("reviews/<int:pk>/",views.vendor_review_detail,name='vendor_review_detail'),
    path("products/delete/<int:pk>/", views.delete_product, name='vendor_delete_product'),
    path("categories/",views.vendor_categories,name='vendor_categories'),
    path("sizes/", views.vendor_sizes, name='vendor_sizes'),
    path("colors/", views.vendor_colors, name='vendor_colors'),
    path("shipments/",views.vendor_shipments,name='vendor_shipments'),
    path('reviews/', views.vendor_reviews, name='vendor_reviews'),
    path("shipments/update/<int:pk>/",views.update_shipment_status,name='update_shipment_status'),
    path("shipments/create/<int:order_item_id>/",views.create_shipment,name='create_shipment'),
    path("profile/",views.vendor_profile,name='vendor_profile'),
    path("analytics/",views.vendor_analytics,name='vendor_analytics'),
    path("help/",views.vendor_help,name='vendor_help'),
    path("change-password/",views.vendor_change_password,name='vendor_change_password'),
]
