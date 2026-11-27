from decimal import Decimal
from .models import Product

class Cart:
    def __init__(self, request):
        self.session = request.session
        cart = self.session.get('cart')
        if not cart:
            cart = self.session['cart'] = {}
        self.cart = cart

    def add(self, product_id, quantity=1, update=False):
        product_id = str(product_id)
        if product_id not in self.cart:
            self.cart[product_id] = {'qty': 0}
        if update:
            self.cart[product_id]['qty'] = quantity
        else:
            self.cart[product_id]['qty'] += quantity
        self.session.modified = True

    def remove(self, product_id):
        product_id = str(product_id)
        if product_id in self.cart:
            del self.cart[product_id]
            self.session.modified = True

    def get_items(self):
        products = Product.objects.filter(id__in=self.cart.keys())
        items = []
        total = 0

        for product in products:
            qty = self.cart[str(product.id)]['qty']
            subtotal = product.price * qty
            total += subtotal
            items.append({
                'product': product,
                'qty': qty,
                'subtotal': subtotal
            })

        return items, total
