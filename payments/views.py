from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from orders.models import Order, OrderItem
from cart.cart import Cart
from orders.views import send_order_notification_email
from .gateway import SafepayGateway


@login_required
def choose_payment(request):
    """
    Payment method selection page.
    Customer yahan decide karta hai ke COD karna hai ya Online Payment.
    """
    cart = Cart(request)
    if len(cart) == 0:
        messages.warning(request, "Your cart is empty.")
        return redirect('cart:cart_detail')

    subtotal = cart.get_subtotal_price()
    shipping = 0 if subtotal >= 5000 else 150
    grand_total = subtotal + shipping

    if request.method == 'POST':
        payment_method = request.POST.get('payment_method')

        if payment_method == 'ONLINE':
            # Step 1: Order banao with PENDING payment status
            with transaction.atomic():
                order = Order.objects.create(
                    user=request.user,
                    first_name=request.POST.get('first_name', ''),
                    phone=request.POST.get('phone', ''),
                    address=request.POST.get('address', ''),
                    city=request.POST.get('city', ''),
                    shipping_cost=shipping,
                    total_cost=grand_total,
                    payment_method='ONLINE',
                    payment_status='PENDING',
                )

                order_total = 0
                for item in cart:
                    db_product = item['product']
                    real_price = db_product.price
                    OrderItem.objects.create(
                        order=order,
                        product=db_product,
                        price=real_price,
                        quantity=item['quantity']
                    )
                    order_total += real_price * item['quantity']

                order.total_cost = order_total + shipping
                order.save()

            # Step 2: Safepay checkout URL generate karo
            gateway = SafepayGateway()
            checkout_url = gateway.create_checkout_url(order, request)

            if checkout_url:
                cart.clear()
                return redirect(checkout_url)
            else:
                messages.error(request, "Payment gateway error. Please try COD or try again later.")
                order.delete()
                return redirect('orders:checkout')

        elif payment_method == 'COD':
            # COD flow (same as before)
            with transaction.atomic():
                order = Order.objects.create(
                    user=request.user,
                    first_name=request.POST.get('first_name', ''),
                    phone=request.POST.get('phone', ''),
                    address=request.POST.get('address', ''),
                    city=request.POST.get('city', ''),
                    shipping_cost=shipping,
                    total_cost=grand_total,
                    payment_method='COD',
                    payment_status='PENDING',
                    status='Pending',
                )

                order_total = 0
                for item in cart:
                    db_product = item['product']
                    real_price = db_product.price
                    OrderItem.objects.create(
                        order=order,
                        product=db_product,
                        price=real_price,
                        quantity=item['quantity']
                    )
                    db_product.stock = max(0, db_product.stock - item['quantity'])
                    db_product.save()
                    order_total += real_price * item['quantity']

                order.total_cost = order_total + shipping
                order.save()

            cart.clear()
            send_order_notification_email(order)
            return redirect('orders:order_success', order_id=order.id)

    # Pre-fill form data
    user_fullname = f"{request.user.first_name} {request.user.last_name}".strip() or request.user.username
    user_phone = request.user.profile.phone if hasattr(request.user, 'profile') else ""

    context = {
        'subtotal': subtotal,
        'shipping': shipping,
        'grand_total': grand_total,
        'cart': cart,
        'user_fullname': user_fullname,
        'user_phone': user_phone,
    }
    return render(request, 'payments/choose_payment.html', context)


def payment_callback(request, order_number):
    """
    Safepay redirects the customer here after payment.
    Hum verify karte hain ke payment actually successful thi ya nahi.
    """
    order = get_object_or_404(Order, order_number=order_number)
    gateway = SafepayGateway()

    is_paid, transaction_id = gateway.verify_payment(order_number)

    if is_paid:
        order.payment_status = 'PAID'
        order.payment_id = transaction_id
        order.status = 'Confirmed'
        order.save()

        # Stock reduce karo (sirf successful payment par)
        for item in order.items.all():
            product = item.product
            product.stock = max(0, product.stock - item.quantity)
            product.save()

        send_order_notification_email(order)
        messages.success(request, "Payment successful! Your order has been confirmed.")
        return redirect('orders:order_success', order_id=order.id)
    else:
        order.payment_status = 'FAILED'
        order.save()
        messages.error(request, "Payment verification failed. Please contact support.")
        return redirect('orders:order_history')


def payment_cancel(request, order_number):
    """
    Customer ne payment page se cancel kiya.
    """
    order = get_object_or_404(Order, order_number=order_number)
    order.payment_status = 'FAILED'
    order.save()
    messages.warning(request, "Payment was cancelled. Your order has not been placed.")
    return redirect('cart:cart_detail')