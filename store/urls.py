from django.conf import settings
from django.conf.urls.static import static
from django.urls import path
from django.contrib.auth import views as auth_views
import django.shortcuts # For test-404 lambda
from . import views

urlpatterns = [
    path("",views.index,name='home'),
    path("admin-panel/",views.admin_login,name='admin_login'),
    path("admin-panel/forgot-password/",views.admin_forgot_password,name='admin_forgot_password'),
    path("vendor-panel/",views.vendor_login,name='vendor_login'),
    path("vendor-panel/forgot-password/",views.vendor_forgot_password,name='vendor_forgot_password'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.registration_view, name='register'),
    path('forgot-password/', views.forgot_password_view, name='forgot_password'),
    path('profile/', views.profile_view, name='profile'),
    path('shop/', views.shop, name='shop'),
    path('product/<slug:slug>/', views.product_detail, name='product_detail'),
    path('product/add_review/<int:product_id>/', views.add_review, name='add_review'),
    path('terms/', views.terms_view, name='terms'),
    path('privacy/', views.privacy_view, name='privacy'),
    path('complaint/', views.complaint_view, name='complaint'),
    path('contact/', views.contact_view, name='contact'),
    path('become-vendor/', views.become_vendor, name='become_vendor'),
    path('vendor-shop/', views.vendor_shop, name='vendor_shop'), # Vendor Shop View
    path('cookie-policy/', views.cookie_policy_view, name='cookie_policy'),
    path('profile/settings/', views.profile_settings, name='profile_settings'),
    path('profile/addresses/', views.address_list, name='address_list'),
    path('profile/addresses/add/', views.address_add, name='address_add'),
    path('profile/addresses/edit/<int:address_id>/', views.address_edit, name='address_edit'),
    path('profile/addresses/delete/<int:address_id>/', views.address_delete, name='address_delete'),
    path('profile/orders/', views.order_list, name='order_list'),
    path('profile/orders/<int:order_id>/', views.order_detail, name='order_detail'),
    path('profile/change-password/', views.change_password, name='change_password'),
    path('profile/reviews/', views.my_reviews, name='my_reviews'),
    path('api/search/', views.api_search, name='api_search'),
    path('api/wishlist/toggle/', views.toggle_wishlist, name='toggle_wishlist'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='password_reset_confirm.html'), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(template_name='password_reset_complete.html'), name='password_reset_complete'),
    path('test-404/', lambda request: django.shortcuts.render(request, '404.html')), # Temporary Test Route
]

