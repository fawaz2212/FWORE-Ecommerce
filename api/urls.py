from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CategoryViewSet, ProductViewSet
from .views import RegisterAPIView, LoginAPIView
from .views import OrdersAPIView, OrderDetailAPIView

router = DefaultRouter()

router.register(
    'products',
    ProductViewSet,
    basename='api-products'
)

router.register(
    'categories',
    CategoryViewSet,
    basename='api-categories'
)

from .views import (
    ProductViewSet,
    CategoryViewSet,
    RegisterAPIView,
    LoginAPIView,
    CustomerProfileAPIView,
    LogoutAPIView,
)

from .views import (
    CartAPIView,
    AddToCartAPIView,
    UpdateCartAPIView,
    RemoveFromCartAPIView,
)

from .views import (
    WishlistAPIView,
    AddToWishlistAPIView,
    RemoveFromWishlistAPIView,
)

from .views import (
    CheckoutAPIView,
    PaymentVerifyAPIView,
)

urlpatterns = [
    path('', include(router.urls)),
    path('register/', RegisterAPIView.as_view(), name='api-register'),
    path('login/', LoginAPIView.as_view(), name='api-login'),
    path('profile/', CustomerProfileAPIView.as_view(), name='api-profile'),
    path('logout/', LogoutAPIView.as_view(), name='api-logout'),
    path('cart/', CartAPIView.as_view(), name='api-cart'),

    path('cart/add/', AddToCartAPIView.as_view(), name='api-cart-add'),

    path(
    'cart/update/<int:product_id>/',
    UpdateCartAPIView.as_view(),
    name='api-cart-update'
),

    path(
    'cart/remove/<int:product_id>/',
    RemoveFromCartAPIView.as_view(),
    name='api-cart-remove'
),

path('wishlist/', WishlistAPIView.as_view(), name='api-wishlist'),

path('wishlist/add/', AddToWishlistAPIView.as_view(), name='api-wishlist-add'),

path('wishlist/remove/<int:product_id>/', RemoveFromWishlistAPIView.as_view(), name='api-wishlist-remove'),
path('orders/', OrdersAPIView.as_view(), name='api-orders'),

path('orders/<int:order_id>/', OrderDetailAPIView.as_view(), name='api-order-detail'),
path(
    'checkout/',
    CheckoutAPIView.as_view(),
    name='api-checkout'
),

path(
    'payment/verify/',
    PaymentVerifyAPIView.as_view(),
    name='api-payment-verify'
),


]