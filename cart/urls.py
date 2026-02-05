
from django.urls import path
from . import views

urlpatterns = [
    path('', views.cart_detail, name='cart_detail'),
    path('add-to-cart/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('remove-from-cart/<int:item_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('wishlist/', views.wishlist_detail, name='wishlist_detail'),
    path('add-ajax/', views.add_to_cart_ajax, name='add_to_cart_ajax'),
    path('checkout/', views.checkout, name='checkout'),
    path('create-order/', views.create_order, name='create_order'),
    path('payment-callback/', views.payment_callback, name='payment_callback'),
    path('update-quantity/', views.update_cart_quantity, name='update_cart_quantity'),
]


