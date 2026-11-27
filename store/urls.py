
from django.urls import path
from django.contrib.auth import views as auth_views

from . import views


urlpatterns = [
    # Products
    path('', views.product_list, name='product_list'),
    path('product/<int:id>/', views.product_detail, name='product_detail'),

    # Cart
    path('add/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('update/<int:product_id>/', views.update_cart, name='update_cart'),
    path('remove/<int:product_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('cart/', views.cart_detail, name='cart_detail'),

    # Checkout and payment
    path('checkout/', views.checkout, name='checkout'),
    path(
        'create-checkout-session/',
        views.create_checkout_session,
        name='create_checkout_session'
    ),
    path('success/', views.payment_success, name='payment_success'),
    path('cancel/', views.payment_cancel, name='payment_cancel'),

    # Authentication
    path(
        'login/',
        auth_views.LoginView.as_view(
            template_name='store/login.html'
        ),
        name='login'
    ),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('register/', views.register, name='register'),

    # Wishlist
    path('wishlist/', views.wishlist, name='wishlist'),
    path(
        'wishlist/toggle/<int:product_id>/',
        views.toggle_wishlist,
        name='toggle_wishlist'
    ),

    # Customer account
    path(
        'account/',
        views.customer_dashboard,
        name='customer_dashboard'
    ),
    path('my-orders/', views.my_orders, name='my_orders'),
    path(
        'my-orders/<int:order_id>/',
        views.order_detail,
        name='order_detail'
    ),
    path('edit-profile/', views.edit_profile, name='edit_profile'),
]
