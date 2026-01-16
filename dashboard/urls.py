from django.urls import path
from . import views

urlpatterns = [
    path("", views.dashboard, name='admin_dashboard'),
    path("users/", views.manage_users, name='manage_users'),
    path("users/add/", views.add_user, name='add_user'),
    path("users/edit/<int:pk>/", views.edit_user, name='edit_user'),
    path("categories/", views.manage_categories, name='manage_categories'),
    path("categories/add/", views.add_category, name='add_category'),
    path("categories/edit/<int:pk>/", views.edit_category, name='edit_category'),
    path("products/", views.manage_products, name='manage_products'),
    path("products/add/", views.add_product, name='admin_add_product'),
    path("products/edit/<int:pk>/", views.edit_product, name='admin_edit_product'),
    path("orders/", views.manage_orders, name='manage_orders'),
    path("orders/<int:pk>/", views.order_detail, name='admin_order_detail'),
    path("payments/", views.manage_payments, name='manage_payments'),
    path("reviews/", views.view_reviews, name='view_reviews'),
    path("complaints/", views.view_complaints, name='view_complaints'),
    path("profile/", views.admin_profile, name='admin_profile'),
    path("change-password/", views.change_password, name='admin_change_password'),
]
