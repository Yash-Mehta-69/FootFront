from django.conf import settings
from django.conf.urls.static import static
from django.urls import path
from django.views.generic import TemplateView
from django.contrib.sitemaps.views import sitemap
from django.urls import path, include
from . import views

urlpatterns = [
    path("",views.index,name='home'),
    path("admin-panel/",views.admin_login,name='admin_login'),
    path("vendor-panel/",views.vendor_login,name='vendor_login'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.registration_view, name='register'),
    path('forgot-password/', views.forgot_password_view, name='forgot_password'),
    path('forgot-password/', views.forgot_password_view, name='forgot_password'),
    path('profile/', views.profile_view, name='profile'),
    path('shop/', views.shop, name='shop'),
    path('product-detail/', views.product_detail, name='product_detail'),


]
