import threading
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from django.db import transaction
from cart.cart import Cart
from .models import Order, OrderItem
from .forms import OrderCreateForm


def _send_email_async(subject, message, from_email, recipient_list):
    """Worker function that runs silently in background thread."""
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=from_email,
            recipient_list=recipient_list,
            fail_silently=True,
        )
    except Exception as e:
        print(f"⚠️ Background email error: {e}")


def send_order_notification_email(order):
    """
    Spawns a fast background thread to send the email notification.
    Checkout completes in 0.1 second without any waiting or loading!
    """
    try:
        items_list = ""
        for item in order.items.all():
            items_list += f"- {item.quantity}x {item.product.name} (Rs. {item.get_cost():,.0f})\n"

        ref = order.order_number or f"Order #{order.id}"
        subject = f"🚨 New Order {ref} — Shah G Cap House"
        message = f"""
Assalamu Alaikum Mashood,

You have received a new order on Shah G Cap House!

========================================
ORDER DETAILS ({ref})
========================================
Customer Name: {order.first_name}
Phone / WhatsApp: {order.phone}
Complete Address: {order.address}
City: {order.city}

========================================
ORDERED ITEMS
========================================
{items_list}
Shipping Fee: Rs. {order.shipping_cost:,.0f}
Grand Total Payable: Rs. {order.total_cost:,.0f}
Payment Method: Cash on Delivery (COD)

========================================
STATUS: {order.status}
Timestamp: {order.created_at.strftime('%d %B %Y, %I:%M %p')}

Please contact the customer on WhatsApp ({order.phone}) to confirm dispatch.
        """

        # ⚡ Run in background thread so customer gets instant response
        email_thread = threading.Thread(
            target=_send_email_async,
            args=(subject, message, settings.DEFAULT_FROM_EMAIL, ['mashoodarshad22@gmail.com']),
            daemon=True
        )
        email_thread.start()

    except Exception as e:
        print(f"⚠️ Email preparation failed: {e}")


def checkout(request):
    """
    Handles checkout form display and secure Cash on Delivery order creation.
    Uses Django Form validation and atomic DB transactions.
    Prices are fetched from DATABASE, not from session (security).
    """
    cart = Cart(request)

    if len(cart) == 0:
        messages.warning(request, "Your shopping bag is empty. Please select an article first.")
        return redirect('cart:cart_detail')

    subtotal_display = cart.get_subtotal_price()
    shipping_cost = 0 if subtotal_display >= 5000 else 150
    grand_total_display = subtotal_display + shipping_cost

    if request.method == 'POST':
        form = OrderCreateForm(request.POST)

        if form.is_valid():
            # 🔒 ATOMIC TRANSACTION: All-or-nothing order creation
            try:
                with transaction.atomic():
                    # Ensure session key exists for guest tracking
                    if not request.session.session_key:
                        request.session.save()

                    # 1. Create Order record
                    order = Order(
                        first_name=form.cleaned_data['first_name'],
                        phone=form.cleaned_data['phone'],
                        address=form.cleaned_data['address'],
                        city=form.cleaned_data['city'],
                        shipping_cost=shipping_cost,
                        total_cost=0,
                        status='Pending',
                        session_key=request.session.session_key,
                    )
                    order.save()

                    # 2. Fetch REAL prices from DATABASE
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

                        # Reduce stock safely
                        db_product.stock = max(0, db_product.stock - item['quantity'])
                        db_product.save()

                        order_total += real_price * item['quantity']

                    # 3. Update order total with real DB-calculated amount
                    order.total_cost = order_total + shipping_cost
                    order.save()

                # 4. Clear cart
                cart.clear()

                # 5. Send instant email notification in background
                send_order_notification_email(order)

                # 6. Redirect to success page
                return redirect('orders:order_success', order_id=order.id)

            except Exception as e:
                print(f"⚠️ Order placement error: {e}")
                messages.error(request, "Something went wrong while placing your order. Please try again.")
                return render(request, 'orders/checkout.html', {
                    'form': form,
                    'cart': cart,
                    'subtotal': subtotal_display,
                    'shipping_fee': shipping_cost,
                    'grand_total': grand_total_display,
                })
        else:
            messages.error(request, "Please correct the errors in the form below.")
    else:
        form = OrderCreateForm()

    context = {
        'form': form,
        'cart': cart,
        'subtotal': subtotal_display,
        'shipping_fee': shipping_cost,
        'grand_total': grand_total_display,
    }
    return render(request, 'orders/checkout.html', context)


def order_success(request, order_id):
    """
    Renders order confirmation screen with 1-Click WhatsApp Connect button.
    """
    order = get_object_or_404(Order, id=order_id)
    return render(request, 'orders/order_success.html', {'order': order})


def order_history(request):
    """
    Shows order history for the current session (guest users).
    """
    session_key = request.session.session_key
    if not session_key:
        orders = Order.objects.none()
    else:
        orders = Order.objects.filter(session_key=session_key)

    return render(request, 'orders/order_history.html', {'orders': orders})


def order_detail(request, order_number):
    """
    Shows detailed view of a specific order for the customer.
    """
    session_key = request.session.session_key
    order = get_object_or_404(Order, order_number=order_number, session_key=session_key)
    return render(request, 'orders/order_detail.html', {'order': order})