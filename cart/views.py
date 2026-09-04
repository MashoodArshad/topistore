import json
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from products.models import Product
from .cart import Cart

FLAT_SHIPPING_FEE = 150  # Fixed nationwide delivery fee

def cart_detail(request):
    """Renders the shopping cart page with fixed shipping."""
    cart = Cart(request)
    subtotal = cart.get_subtotal_price()
    shipping_fee = FLAT_SHIPPING_FEE if len(cart) > 0 else 0
    grand_total = subtotal + shipping_fee

    context = {
        'cart': cart,
        'subtotal': subtotal,
        'shipping_fee': shipping_fee,
        'grand_total': grand_total,
    }
    return render(request, 'cart/cart_detail.html', context)

def cart_add(request, product_id):
    """Adds an item to the cart."""
    cart = Cart(request)
    product = get_object_or_404(Product, id=product_id)
    cart.add(product=product, quantity=1, override_quantity=False)
    return redirect('cart:cart_detail')

def cart_remove(request, product_id):
    """Removes an item from the cart."""
    cart = Cart(request)
    product = get_object_or_404(Product, id=product_id)
    cart.remove(product)
    return redirect('cart:cart_detail')

@require_POST
def cart_update_qty_ajax(request):
    """
    Asynchronously updates cart quantity and returns totals with flat shipping.
    """
    cart = Cart(request)
    try:
        data = json.loads(request.body)
        product_id = str(data.get('product_id'))
        new_qty = int(data.get('quantity'))

        product = Product.objects.get(id=product_id)

        if new_qty > product.stock:
            return JsonResponse({
                'success': False, 
                'message': f"Only {product.stock} items available in stock."
            }, status=400)

        if new_qty < 1:
            return JsonResponse({
                'success': False, 
                'message': "Quantity must be at least 1."
            }, status=400)

        cart.add(product=product, quantity=new_qty, override_quantity=True)

        item_total = 0
        for item in cart:
            if str(item['product'].id) == product_id:
                item_total = item['total_price']

        subtotal = cart.get_subtotal_price()
        shipping = FLAT_SHIPPING_FEE if len(cart) > 0 else 0
        grand_total = subtotal + shipping

        return JsonResponse({
            'success': True,
            'cart_subtotal': f"{subtotal:,.0f}",
            'cart_grandtotal': f"{grand_total:,.0f}",
            'item_subtotal': f"{item_total:,.0f}",
            'cart_count': len(cart)
        })

    except Product.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Product not found.'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)