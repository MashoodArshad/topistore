from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from cart.cart import Cart
from .models import Order, OrderItem


def checkout(request):
    """
    Handles checkout form display and Cash on Delivery order creation.
    """
    cart = Cart(request)

    # Agar cart empty ho toh user ko wapas cart page bhej do
    if len(cart) == 0:
        messages.warning(request, "Your shopping bag is empty. Please select an article first.")
        return redirect('cart:cart_detail')

    subtotal = cart.get_subtotal_price()
    shipping_cost = 0 if subtotal >= 5000 else 150
    grand_total = subtotal + shipping_cost

    if request.method == 'POST':
        # Form se customer ka data read karein
        first_name = request.POST.get('first_name', '').strip()
        phone = request.POST.get('phone', '').strip()
        address = request.POST.get('address', '').strip()
        city = request.POST.get('city', '').strip()

        # Validation check
        if not (first_name and phone and address and city):
            messages.error(request, "Please fill in all required delivery details.")
            return render(request, 'orders/checkout.html', {
                'cart': cart,
                'subtotal': subtotal,
                'shipping_fee': shipping_cost,
                'grand_total': grand_total,
            })

        # 1. Create main Order in Supabase Database
        order = Order.objects.create(
            first_name=first_name,
            phone=phone,
            address=address,
            city=city,
            shipping_cost=shipping_cost,
            total_cost=grand_total,
            status='Pending'
        )

        # 2. Save ordered items and decrement product stock
        for item in cart:
            OrderItem.objects.create(
                order=order,
                product=item['product'],
                price=item['price'],
                quantity=item['quantity']
            )
            
            # Reduce inventory stock
            product = item['product']
            product.stock = max(0, product.stock - item['quantity'])
            product.save()

        # 3. Clear shopping session cart
        cart.clear()

        # 4. Redirect to Order Success Page
        return redirect('orders:order_success', order_id=order.id)

    # GET Request: Render Checkout Page
    context = {
        'cart': cart,
        'subtotal': subtotal,
        'shipping_fee': shipping_cost,
        'grand_total': grand_total,
    }
    return render(request, 'orders/checkout.html', context)


def order_success(request, order_id):
    """
    Renders a premium order confirmation screen for the customer.
    """
    order = get_object_or_404(Order, id=order_id)
    return render(request, 'orders/order_success.html', {'order': order})