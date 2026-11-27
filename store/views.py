
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from .models import Product, Wishlist, RecentlyViewed
from django.shortcuts import render, get_object_or_404,redirect
from .models import Product
from .models import Product
from .cart import Cart
from django.contrib.auth.forms import UserCreationForm
import stripe
from decimal import Decimal
import stripe

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required

from .cart import Cart
from .models import (
    Product,
    Order,
    OrderItem,
    CustomerProfile,
)

from django.db.models import Q
from .models import Product, Category
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.shortcuts import render, get_object_or_404
from .models import Order, OrderItem
from .models import CustomerProfile
from .forms import CustomerProfileForm
from django.db import transaction





def product_list(request):
    products = Product.objects.filter(available=True)

    # Search
    search_query = request.GET.get('q', '').strip()

    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query)
        )

    # Category filter
    category_slug = request.GET.get('category', '')

    if category_slug:
        products = products.filter(
            category__slug=category_slug
        )

    # Minimum price
    min_price = request.GET.get('min_price', '')

    if min_price:
        try:
            products = products.filter(price__gte=float(min_price))
        except (ValueError, TypeError):
            min_price = ''

    # Maximum price
    max_price = request.GET.get('max_price', '')

    if max_price:
        try:
            products = products.filter(price__lte=float(max_price))
        except (ValueError, TypeError):
            max_price = ''

    # Sorting
    sort = request.GET.get('sort', '')

    if sort == 'price_low':
        products = products.order_by('price')

    elif sort == 'price_high':
        products = products.order_by('-price')

    elif sort == 'newest':
        products = products.order_by('-created_at')

    categories = Category.objects.all().order_by('name')

    context = {
        'products': products,
        'categories': categories,
        'search_query': search_query,
        'selected_category': category_slug,
        'min_price': min_price,
        'max_price': max_price,
        'selected_sort': sort,
    }

    return render(
        request,
        'store/product_list.html',
        context
    )



def product_detail(request, id):
    product = get_object_or_404(
        Product,
        id=id,
        available=True
    )

    # Create session for guest visitors
    if not request.session.session_key:
        request.session.create()

    # Save recently viewed product
    if request.user.is_authenticated:
        RecentlyViewed.objects.update_or_create(
            user=request.user,
            product=product,
            defaults={'session_key': ''}
        )

        recent_products = RecentlyViewed.objects.filter(
            user=request.user
        ).exclude(product=product).select_related('product')[:4]

        is_wishlisted = Wishlist.objects.filter(
            user=request.user,
            product=product
        ).exists()

    else:
        RecentlyViewed.objects.update_or_create(
            session_key=request.session.session_key,
            product=product,
            defaults={'user': None}
        )

        recent_products = RecentlyViewed.objects.filter(
            session_key=request.session.session_key
        ).exclude(product=product).select_related('product')[:4]

        is_wishlisted = False

    # Related products
    related_products = Product.objects.filter(
        category=product.category,
        available=True
    ).exclude(id=product.id)[:4]

    return render(
        request,
        'store/product_detail.html',
        {
            'product': product,
            'related_products': related_products,
            'recent_products': recent_products,
            'is_wishlisted': is_wishlisted,
        }
    )


def add_to_cart(request, product_id):
    cart = Cart(request)
    cart.add(product_id)
    messages.success(request, "Product added to cart 🛒")
    return redirect('cart_detail')

def update_cart(request, product_id):
    qty = int(request.POST.get('quantity'))
    cart = Cart(request)
    cart.add(product_id, quantity=qty, update=True)
    return redirect('cart_detail')

def remove_from_cart(request, product_id):
    cart = Cart(request)
    cart.remove(product_id)
    return redirect('cart_detail')

def cart_detail(request):
    cart = Cart(request)
    items, total = cart.get_items()
    return render(request, 'store/cart.html', {'items': items, 'total': total})


@login_required
def checkout(request):
    cart = Cart(request)
    items, total = cart.get_items()

    if not items:
        messages.warning(request, "Your cart is empty.")
        return redirect('cart_detail')

    profile, created = CustomerProfile.objects.get_or_create(
        user=request.user
    )

    context = {
        'items': items,
        'total': total,
        'profile': profile,
        'user': request.user,
    }

    return render(request, 'store/checkout.html', context)


@login_required
def create_checkout_session(request):
    if request.method != 'POST':
        return redirect('checkout')

    stripe.api_key = settings.STRIPE_SECRET_KEY

    cart = Cart(request)
    items, total = cart.get_items()

    if not items or total <= 0:
        messages.error(request, "Your cart is empty.")
        return redirect('cart_detail')

    # Get delivery details
    full_name = request.POST.get('full_name', '').strip()
    phone = request.POST.get('phone', '').strip()
    address = request.POST.get('address', '').strip()
    city = request.POST.get('city', '').strip()
    postal_code = request.POST.get('postal_code', '').strip()
    email = request.POST.get('email', '').strip()

    if not all([
        full_name, phone, address,
        city, postal_code, email
    ]):
        messages.error(request, "Please complete all delivery details.")
        return redirect('checkout')

    # Save a snapshot of the cart for after payment
    order_items = []

    for item in items:
        order_items.append({
            'product_id': item['product'].id,
            'product_name': item['product'].name,
            'price': str(item['product'].price),
            'quantity': item['qty'],
        })

    pending_order = {
        'user_id': request.user.id,
        'full_name': full_name,
        'email': email,
        'phone': phone,
        'address': address,
        'city': city,
        'postal_code': postal_code,
        'total_amount': str(total),
        'items': order_items,
    }

    # Stripe uses the smallest currency unit
    amount_in_paise = int(
        (Decimal(str(total)) * 100).quantize(Decimal('1'))
    )

    session = stripe.checkout.Session.create(
        mode='payment',
        payment_method_types=['card'],
        line_items=[{
            'price_data': {
                'currency': 'inr',
                'product_data': {
                    'name': "FWORE'S Order Payment",
                },
                'unit_amount': amount_in_paise,
            },
            'quantity': 1,
        }],
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

    # Store the order snapshot against this Stripe session
    pending_orders = request.session.get('pending_orders', {})
    pending_orders[session.id] = pending_order
    request.session['pending_orders'] = pending_orders
    request.session.modified = True

    return redirect(session.url)


@login_required
def payment_success(request):
    stripe.api_key = settings.STRIPE_SECRET_KEY

    session_id = request.GET.get('session_id')

    if not session_id:
        messages.error(request, "Missing payment session.")
        return redirect('my_orders')

    # Verify payment directly with Stripe
    session = stripe.checkout.Session.retrieve(session_id)

    if (
        session.payment_status != 'paid'
        or session.client_reference_id != str(request.user.id)
    ):
        messages.error(request, "Payment has not been completed.")
        return redirect('my_orders')

    # Avoid creating duplicate orders for this Stripe session
    order, created = Order.objects.get_or_create(
        stripe_session_id=session.id,
        defaults={
            'user': request.user,
            'full_name': '',
            'email': request.user.email,
            'phone': '',
            'address': '',
            'city': '',
            'postal_code': '',
            'total_amount': Decimal(session.amount_total) / Decimal('100'),
            'payment_status': 'paid',
            'order_status': 'processing',
        }
    )

    if created:
        pending_orders = request.session.get('pending_orders', {})
        snapshot = pending_orders.get(session.id)

        if not snapshot or snapshot['user_id'] != request.user.id:
            order.delete()
            messages.error(
                request,
                "Checkout details were not found. Please contact support."
            )
            return redirect('my_orders')

        order.full_name = snapshot['full_name']
        order.email = snapshot['email']
        order.phone = snapshot['phone']
        order.address = snapshot['address']
        order.city = snapshot['city']
        order.postal_code = snapshot['postal_code']
        order.total_amount = Decimal(str(snapshot['total_amount']))
        order.save()

        for item in snapshot['items']:
            OrderItem.objects.create(
                order=order,
                product_id=item['product_id'],
                product_name=item['product_name'],
                price=Decimal(item['price']),
                quantity=item['quantity'],
            )

        # Clear cart only after successful payment and order creation
        cart = Cart(request)
        cart.cart.clear()
        request.session.modified = True

        del pending_orders[session.id]
        request.session['pending_orders'] = pending_orders
        request.session.modified = True

    return render(
        request,
        'store/success.html',
        {'order': order}
    )


def payment_cancel(request):
    return render(request, 'store/cancel.html')




def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Account created successfully!')
            return redirect('login')
    else:
        form = UserCreationForm()
    return render(request, 'store/register.html', {'form': form})




def payment_success(request):
    return render(request, 'store/success.html')

def payment_cancel(request):
    return render(request, 'store/cancel.html')





@login_required
@require_POST
def wishlist(request):
    products = Product.objects.filter(
        wishlist__user=request.user
    ).distinct()

    return render(
        request,
        'store/wishlist.html',
        {'products': products}
    )


@login_required
def payment_success(request):
    stripe.api_key = settings.STRIPE_SECRET_KEY

    session_id = request.GET.get('session_id')

    if not session_id:
        messages.error(request, "Missing payment session.")
        return redirect('my_orders')

    session = stripe.checkout.Session.retrieve(session_id)

    if (
        session.payment_status != 'paid'
        or session.client_reference_id != str(request.user.id)
    ):
        messages.error(request, "Payment could not be verified.")
        return redirect('my_orders')

    # Check whether this payment already has an order
    order = Order.objects.filter(
        stripe_session_id=session.id,
        user=request.user
    ).first()

    if order:
        return render(
            request,
            'store/success.html',
            {'order': order}
        )

    pending_orders = request.session.get('pending_orders', {})
    snapshot = pending_orders.get(session.id)

    if not snapshot or snapshot['user_id'] != request.user.id:
        messages.error(
            request,
            "Checkout details not found. Please contact support."
        )
        return redirect('my_orders')

    if int(session.amount_total or 0) != int(
        Decimal(snapshot['total_amount']) * 100
    ):
        messages.error(request, "Payment amount does not match the order.")
        return redirect('my_orders')

    with transaction.atomic():

        order = Order.objects.create(
            stripe_session_id=session.id,
            user=request.user,
            full_name=snapshot['full_name'],
            email=snapshot['email'],
            phone=snapshot['phone'],
            address=snapshot['address'],
            city=snapshot['city'],
            postal_code=snapshot['postal_code'],
            total_amount=Decimal(session.amount_total) / Decimal('100'),
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

    # Clear cart only after successful order creation
    cart = Cart(request)
    cart.cart.clear()
    request.session.modified = True

    del pending_orders[session.id]
    request.session['pending_orders'] = pending_orders
    request.session.modified = True

    return render(
        request,
        'store/success.html',
        {'order': order}
    )


@login_required
def wishlist(request):
    products = Product.objects.filter(
        wishlist__user=request.user
    ).distinct()

    return render(
        request,
        'store/wishlist.html',
        {'products': products}
    )


@login_required
def toggle_wishlist(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    wishlist_item, created = Wishlist.objects.get_or_create(
        user=request.user,
        product=product
    )

    if created:
        messages.success(request, 'Added to your wishlist ❤️')
    else:
        wishlist_item.delete()
        messages.info(request, 'Removed from your wishlist.')

    return redirect(
        request.META.get('HTTP_REFERER', 'product_list')
    )



@login_required
def customer_dashboard(request):
    orders = Order.objects.filter(
        user=request.user
    ).order_by('-created_at')

    total_orders = orders.count()

    total_spent = orders.filter(
        payment_status='paid'
    ).aggregate(
        total=Sum('total_amount')
    )['total'] or 0

    recent_orders = orders[:5]

    context = {
        'total_orders': total_orders,
        'total_spent': total_spent,
        'recent_orders': recent_orders,
    }

    return render(
        request,
        'store/customer_dashboard.html',
        context
    )


@login_required
def my_orders(request):
    orders = Order.objects.filter(
        user=request.user
    ).order_by('-created_at')

    return render(
        request,
        'store/my_orders.html',
        {'orders': orders}
    )


@login_required
def order_detail(request, order_id):
    order = get_object_or_404(
        Order.objects.prefetch_related('items'),
        id=order_id,
        user=request.user
    )

    return render(
        request,
        'store/order_detail.html',
        {'order': order}
    )


@login_required
def edit_profile(request):

    profile, created = CustomerProfile.objects.get_or_create(
        user=request.user
    )

    if request.method == 'POST':
        form = CustomerProfileForm(
            request.POST,
            instance=profile
        )

        if form.is_valid():
            form.save()
            messages.success(
                request,
                'Your profile has been updated successfully!'
            )
            return redirect('edit_profile')

    else:
        form = CustomerProfileForm(instance=profile)

    return render(
        request,
        'store/edit_profile.html',
        {'form': form}
    )