from decimal import Decimal

import stripe

from django.conf import settings
from django.contrib.auth.models import User
from django.db import transaction
from django.utils import timezone

from rest_framework import (
    viewsets,
    generics,
    permissions,
    status,
)
from rest_framework.authtoken.models import Token
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated

from store.models import (
    Product,
    Category,
    Wishlist,
    Order,
    OrderItem,
)
from store.cart import Cart

from .serializers import (
    RegisterSerializer,
    ProductSerializer,
    CategorySerializer,
)

class ProductViewSet(viewsets.ReadOnlyModelViewSet):

    queryset = Product.objects.filter(
        available=True
    ).order_by('-created_at')

    serializer_class = ProductSerializer


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):

    queryset = Category.objects.all().order_by('name')

    serializer_class = CategorySerializer


class RegisterAPIView(generics.CreateAPIView):

    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]


class LoginAPIView(APIView):

    permission_classes = [permissions.AllowAny]

    def post(self, request):

        from django.contrib.auth import authenticate

        username = request.data.get('username')
        password = request.data.get('password')

        user = authenticate(
            username=username,
            password=password
        )

        if user is None:
            return Response(
                {'error': 'Invalid username or password.'},
                status=400
            )

        token, created = Token.objects.get_or_create(user=user)

        return Response({
            'message': 'Login successful.',
            'token': token.key,
            'username': user.username,
        })


class CustomerProfileAPIView(APIView):

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response({
            'id': request.user.id,
            'username': request.user.username,
            'email': request.user.email,
        })


class LogoutAPIView(APIView):

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        request.auth.delete()

        return Response({
            'message': 'Logout successful.'
        })




# ==========================================
# CART API
# ==========================================

class CartAPIView(APIView):

    permission_classes = [AllowAny]

    def get(self, request):

        cart = Cart(request)
        items, total = cart.get_items()

        cart_items = []

        for item in items:
            product = item['product']

            image_url = None

            if product.image:
                image_url = request.build_absolute_uri(
                    product.image.url
                )

            cart_items.append({
                'product_id': product.id,
                'name': product.name,
                'price': str(product.price),
                'quantity': item['qty'],
                'subtotal': str(item['subtotal']),
                'image': image_url,
            })

        return Response({
            'items': cart_items,
            'total_items': sum(
                item['qty'] for item in items
            ),
            'total': str(total),
        })


class AddToCartAPIView(APIView):

    permission_classes = [AllowAny]

    def post(self, request):

        product_id = request.data.get('product_id')

        try:
            quantity = int(request.data.get('quantity', 1))
        except (ValueError, TypeError):
            return Response(
                {'error': 'Invalid quantity.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if quantity < 1:
            return Response(
                {'error': 'Quantity must be at least 1.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        product = Product.objects.filter(
            id=product_id,
            available=True
        ).first()

        if not product:
            return Response(
                {'error': 'Product not found or unavailable.'},
                status=status.HTTP_404_NOT_FOUND
            )

        cart = Cart(request)
        cart.add(product.id, quantity=quantity)

        return Response({
            'message': 'Product added to cart.',
            'product_id': product.id,
            'quantity_added': quantity,
        }, status=status.HTTP_200_OK)


class UpdateCartAPIView(APIView):

    permission_classes = [AllowAny]

    def patch(self, request, product_id):

        try:
            quantity = int(request.data.get('quantity'))
        except (ValueError, TypeError):
            return Response(
                {'error': 'Enter a valid quantity.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if quantity < 1:
            return Response(
                {'error': 'Quantity must be at least 1.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        product = Product.objects.filter(
            id=product_id,
            available=True
        ).first()

        if not product:
            return Response(
                {'error': 'Product not found or unavailable.'},
                status=status.HTTP_404_NOT_FOUND
            )

        cart = Cart(request)

        if str(product_id) not in cart.cart:
            return Response(
                {'error': 'Product is not in your cart.'},
                status=status.HTTP_404_NOT_FOUND
            )

        cart.add(
            product_id,
            quantity=quantity,
            update=True
        )

        return Response({
            'message': 'Cart quantity updated.',
            'product_id': product_id,
            'quantity': quantity,
        })


class RemoveFromCartAPIView(APIView):

    permission_classes = [AllowAny]

    def delete(self, request, product_id):

        cart = Cart(request)

        if str(product_id) not in cart.cart:
            return Response(
                {'error': 'Product is not in your cart.'},
                status=status.HTTP_404_NOT_FOUND
            )

        cart.remove(product_id)

        return Response({
            'message': 'Product removed from cart.'
        })






class WishlistAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        wishlist_items = Wishlist.objects.filter(
            user=request.user
        ).select_related('product')

        items = []

        for item in wishlist_items:
            product = item.product

            image_url = None
            if product.image:
                image_url = request.build_absolute_uri(
                    product.image.url
                )

            items.append({
                'wishlist_id': item.id,
                'product_id': product.id,
                'name': product.name,
                'price': str(product.price),
                'image': image_url,
                'created_at': item.created_at,
            })

        return Response({
            'items': items,
            'total_items': len(items)
        })


class AddToWishlistAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        product_id = request.data.get('product_id')

        if not product_id:
            return Response(
                {'error': 'Product ID is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        product = Product.objects.filter(id=product_id).first()

        if not product:
            return Response(
                {'error': 'Product not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

        wishlist_item, created = Wishlist.objects.get_or_create(
            user=request.user,
            product=product
        )

        if created:
            return Response({
                'message': 'Product added to wishlist.',
                'product_id': product.id
            }, status=status.HTTP_201_CREATED)

        return Response({
            'message': 'Product is already in your wishlist.',
            'product_id': product.id
        }, status=status.HTTP_200_OK)


class RemoveFromWishlistAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, product_id):
        wishlist_item = Wishlist.objects.filter(
            user=request.user,
            product_id=product_id
        ).first()

        if not wishlist_item:
            return Response(
                {'error': 'Product not found in wishlist.'},
                status=status.HTTP_404_NOT_FOUND
            )

        wishlist_item.delete()

        return Response({
            'message': 'Product removed from wishlist.'
        }, status=status.HTTP_200_OK)



class OrdersAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        orders = Order.objects.filter(
            user=request.user
        ).prefetch_related('items').order_by('-created_at')

        data = []

        for order in orders:
            order_items = []

            for item in order.items.all():
                order_items.append({
                    'product_id': item.product_id,
                    'product_name': item.product_name,
                    'price': str(item.price),
                    'quantity': item.quantity,
                    'subtotal': str(item.price * item.quantity),
                })

            data.append({
                'id': order.id,
                'full_name': order.full_name,
                'total_amount': str(order.total_amount),
                'order_status': order.order_status,
                'payment_status': order.payment_status,
                'created_at': order.created_at,
                'items': order_items,
            })

        return Response({
            'total_orders': len(data),
            'orders': data,
        })


class OrderDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, order_id):
        order = Order.objects.filter(
            id=order_id,
            user=request.user
        ).prefetch_related('items').first()

        if not order:
            return Response(
                {'error': 'Order not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

        order_items = []

        for item in order.items.all():
            order_items.append({
                'product_id': item.product_id,
                'product_name': item.product_name,
                'price': str(item.price),
                'quantity': item.quantity,
                'subtotal': str(item.price * item.quantity),
            })

        return Response({
            'id': order.id,
            'full_name': order.full_name,
            'email': order.email,
            'phone': order.phone,
            'address': order.address,
            'city': order.city,
            'postal_code': order.postal_code,
            'total_amount': str(order.total_amount),
            'order_status': order.order_status,
            'payment_status': order.payment_status,
            'created_at': order.created_at,
            'items': order_items,
        })



class CheckoutAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):

        cart = Cart(request)
        items, total = cart.get_items()

        if not items or total <= 0:
            return Response(
                {'error': 'Your cart is empty.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate delivery details
        required_fields = [
            'full_name',
            'email',
            'phone',
            'address',
            'city',
            'postal_code',
        ]

        details = {}

        for field in required_fields:
            value = request.data.get(field, '')
            details[field] = str(value).strip()

            if not details[field]:
                return Response(
                    {'error': f'{field} is required.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

        postal_code = details['postal_code']

        if not postal_code.isdigit() or len(postal_code) != 6:
            return Response(
                {'error': 'Enter a valid 6-digit PIN code.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Verify product availability and calculate total
        order_items = []
        total = Decimal('0.00')

        for item in items:
            product = item['product']

            if not product.available:
                return Response(
                    {
                        'error': f'{product.name} is unavailable.'
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            quantity = int(item['qty'])
            price = Decimal(str(product.price))

            total += price * quantity

            order_items.append({
                'product_id': product.id,
                'product_name': product.name,
                'price': str(price),
                'quantity': quantity,
            })

        pending_order = {
            'user_id': request.user.id,
            **details,
            'total_amount': str(total),
            'items': order_items,
        }

        try:
            stripe.api_key = settings.STRIPE_SECRET_KEY

            session = stripe.checkout.Session.create(
                mode='payment',
                payment_method_types=['card'],

                line_items=[
                    {
                        'price_data': {
                            'currency': 'inr',
                            'product_data': {
                                'name': "FWORE'S Order Payment",
                            },
                            'unit_amount': int(total * 100),
                        },
                        'quantity': 1,
                    }
                ],

                client_reference_id=str(request.user.id),

                metadata={
                    'user_id': str(request.user.id),
                },

                success_url=(
                    request.build_absolute_uri('/success/')
                    + '?session_id={CHECKOUT_SESSION_ID}'
                ),

                cancel_url=request.build_absolute_uri('/cancel/'),
            )

            pending_orders = request.session.get(
                'pending_orders', {}
            )

            pending_orders[session.id] = pending_order

            request.session['pending_orders'] = pending_orders
            request.session.modified = True

            return Response({
                'message': 'Stripe checkout session created.',
                'session_id': session.id,
                'checkout_url': session.url,
                'total_amount': str(total),
            }, status=status.HTTP_201_CREATED)

        except Exception:
            return Response(
                {
                    'error': 'Unable to create Stripe checkout session.'
                },
                status=status.HTTP_400_BAD_REQUEST
            )




class PaymentVerifyAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):

        session_id = request.data.get('session_id')

        if not session_id:
            return Response(
                {'error': 'Stripe session ID is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check whether the order already exists
        existing_order = Order.objects.filter(
            stripe_session_id=session_id,
            user=request.user
        ).first()

        if existing_order:
            return Response({
                'message': 'Order already created.',
                'order_id': existing_order.id,
                'payment_status': existing_order.payment_status,
                'order_status': existing_order.order_status,
                'total_amount': str(existing_order.total_amount),
            }, status=status.HTTP_200_OK)

        # Get pending checkout details from the same session
        pending_orders = request.session.get('pending_orders', {})
        snapshot = pending_orders.get(session_id)

        if not snapshot:
            return Response(
                {'error': 'Checkout details not found. Use the same session cookie used during checkout.'},
                status=status.HTTP_404_NOT_FOUND
            )

        if str(snapshot.get('user_id')) != str(request.user.id):
            return Response(
                {'error': 'Checkout user does not match the logged-in user.'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Retrieve Stripe Checkout Session
        try:
            stripe.api_key = settings.STRIPE_SECRET_KEY

            stripe_session = stripe.checkout.Session.retrieve(
                session_id
            )

        except stripe.error.StripeError as e:
            print('Stripe verification error:', str(e))

            return Response(
                {'error': 'Unable to retrieve Stripe payment details.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Verify payment status
        if stripe_session.payment_status != 'paid':
            return Response({
                'error': 'Stripe payment is not completed.',
                'payment_status': stripe_session.payment_status,
                'session_status': stripe_session.status,
            }, status=status.HTTP_400_BAD_REQUEST)

        # Verify customer/user ID
        stripe_user_id = (
            stripe_session.client_reference_id
            or stripe_session.metadata.get('user_id')
        )

        if str(stripe_user_id) != str(request.user.id):
            return Response({
                'error': 'Stripe user ID does not match.',
                'stripe_user_id': stripe_user_id,
                'logged_in_user_id': str(request.user.id),
            }, status=status.HTTP_403_FORBIDDEN)

        # Verify amount and currency
        expected_amount = int(
            Decimal(snapshot['total_amount']) * 100
        )

        if (
            stripe_session.amount_total != expected_amount
            or stripe_session.currency != 'inr'
        ):
            return Response(
                {'error': 'Payment amount or currency does not match.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Create order only after successful verification
        try:
            with transaction.atomic():

                order = Order.objects.create(
                    stripe_session_id=stripe_session.id,
                    user=request.user,
                    full_name=snapshot['full_name'],
                    email=snapshot['email'],
                    phone=snapshot['phone'],
                    address=snapshot['address'],
                    city=snapshot['city'],
                    postal_code=snapshot['postal_code'],
                    total_amount=Decimal(stripe_session.amount_total) / 100,
                    payment_status='paid',
                    order_status='processing',
                )

                for item in snapshot['items']:

                    product = Product.objects.filter(
                        id=item['product_id']
                    ).first()

                    OrderItem.objects.create(
                        order=order,
                        product=product,
                        product_name=item['product_name'],
                        price=Decimal(item['price']),
                        quantity=item['quantity'],
                    )

        except Exception as e:
            print('Order creation error:', str(e))

            return Response(
                {'error': 'Unable to create your order.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Clear cart after successful order creation
        cart = Cart(request)
        cart.cart.clear()

        # Remove pending checkout details
        pending_orders.pop(session_id, None)
        request.session['pending_orders'] = pending_orders
        request.session.modified = True

        return Response({
            'message': 'Payment verified and order created successfully.',
            'order_id': order.id,
            'payment_status': order.payment_status,
            'order_status': order.order_status,
            'total_amount': str(order.total_amount),
        }, status=status.HTTP_201_CREATED)
