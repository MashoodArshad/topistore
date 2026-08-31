from decimal import Decimal
from django.conf import settings
from products.models import Product


class Cart:
    """
    Session-based shopping cart for Shah G Cap House.
    Manages items, quantities, and price calculations in user session.
    """
    def __init__(self, request):
        self.session = request.session
        cart = self.session.get('cart')
        if not cart:
            cart = self.session['cart'] = {}
        self.cart = cart

    def add(self, product, quantity=1, override_quantity=False):
        """
        Add a product to the cart or update its quantity.
        """
        product_id = str(product.id)
        if product_id not in self.cart:
            self.cart[product_id] = {
                'quantity': 0,
                'price': str(product.price)
            }

        if override_quantity:
            self.cart[product_id]['quantity'] = quantity
        else:
            self.cart[product_id]['quantity'] += quantity

        # Ensure quantity does not exceed available product stock
        if self.cart[product_id]['quantity'] > product.stock:
            self.cart[product_id]['quantity'] = product.stock

        # Ensure minimum quantity is 1
        if self.cart[product_id]['quantity'] < 1:
            self.cart[product_id]['quantity'] = 1

        self.save()

    def update_quantity(self, product, quantity):
        """
        Update the quantity of a specific product in the cart.
        Validates against available stock and minimum of 1.
        """
        product_id = str(product.id)
        if product_id in self.cart:
            # Clamp quantity between 1 and available stock
            quantity = max(1, min(quantity, product.stock))
            self.cart[product_id]['quantity'] = quantity
            # Update price to current product price
            self.cart[product_id]['price'] = str(product.price)
            self.save()

    def save(self):
        """Mark session as modified to ensure it gets saved."""
        self.session.modified = True

    def remove(self, product):
        """Remove a product from the cart completely."""
        product_id = str(product.id)
        if product_id in self.cart:
            del self.cart[product_id]
            self.save()

    def __iter__(self):
        """
        Iterate over cart items, fetch fresh product data from DB,
        and re-validate stock and active status.
        """
        product_ids = self.cart.keys()
        # Only fetch active products (handles deactivated items)
        products = Product.objects.filter(id__in=product_ids, is_active=True)
        cart = self.cart.copy()

        for product in products:
            pid = str(product.id)
            cart[pid]['product'] = product
            # Re-sync price with current DB price
            cart[pid]['price'] = str(product.price)
            # Re-validate stock (if stock decreased after adding)
            if cart[pid]['quantity'] > product.stock:
                cart[pid]['quantity'] = product.stock

        for item in cart.values():
            if 'product' in item:
                item['price'] = Decimal(item['price'])
                item['total_price'] = item['price'] * item['quantity']
                yield item

    def __len__(self):
        """Count all items in the cart (sum of quantities)."""
        return sum(item['quantity'] for item in self.cart.values())

    def get_subtotal_price(self):
        """Calculate total price of all items in cart."""
        return sum(
            Decimal(item['price']) * item['quantity']
            for item in self.cart.values()
        )

    def clear(self):
        """Remove cart from session (used after checkout)."""
        if 'cart' in self.session:
            del self.session['cart']
            self.save()