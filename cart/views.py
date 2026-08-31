from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from django.contrib import messages
from products.models import Product
from .cart import Cart


def cart_detail(request):
    """
    Renders the cart page with all items currently stored in session.
    """
    cart = Cart(request)
    subtotal = cart.get_subtotal_price()

    # Flat delivery fee across Pakistan (Free shipping over Rs. 5,000)
    if subtotal > 0:
        shipping_fee = 0 if subtotal >= 5000 else 150
        grand_total = subtotal + shipping_fee
    else:
        shipping_fee = 0
        grand_total = 0

    context = {
        'cart': cart,
        'subtotal': subtotal,
        'shipping_fee': shipping_fee,
        'grand_total': grand_total,
    }
    return render(request, 'cart/cart_detail.html', context)


@require_POST
def cart_add(request, product_id):
    """
    Adds a product to the cart with specified quantity from product detail page.
    """
    cart = Cart(request)
    product = get_object_or_404(Product, id=product_id, is_active=True)

    try:
        quantity = int(request.POST.get('quantity', 1))
    except (ValueError, TypeError):
        quantity = 1

    if quantity < 1:
        quantity = 1

    cart.add(product=product, quantity=quantity)
    messages.success(request, f'"{product.name}" has been added to your shopping bag.')
    return redirect('cart:cart_detail')


@require_POST
def cart_update(request, product_id):
    """
    Updates the quantity of a specific product in the cart.
    Called from the cart detail page via +/- buttons.
    """
    cart = Cart(request)
    product = get_object_or_404(Product, id=product_id, is_active=True)

    try:
        quantity = int(request.POST.get('quantity', 1))
    except (ValueError, TypeError):
        quantity = 1

    cart.update_quantity(product=product, quantity=quantity)
    return redirect('cart:cart_detail')


@require_POST
def cart_remove(request, product_id):
    """
    Removes a product completely from the shopping cart.
    """
    cart = Cart(request)
    product = get_object_or_404(Product, id=product_id)
    cart.remove(product)
    messages.info(request, f'"{product.name}" has been removed from your bag.')
    return redirect('cart:cart_detail')