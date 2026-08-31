import os
import json
import urllib.request
import threading
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import transaction
from cart.cart import Cart
from .models import Order, OrderItem
from .forms import OrderCreateForm


def _send_email_via_resend_api(subject, message_text, recipient_email):
    """
    Sends email via Resend HTTPS REST API (Port 443).
    Bypasses all cloud SMTP port blocking on Render for 100% delivery!
    """
    api_key = os.getenv('RESEND_API_KEY', '').strip()
    if not api_key:
        print("⚠️ RESEND_API_KEY is missing. Email skipped.")
        return

    url = "https://api.resend.com/emails"
    payload = {
        "from": "Shah G Cap House <onboarding@resend.dev>",
        "to": [recipient_email],
        "subject": subject,
        "text": message_text
    }

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode('utf-8'),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "ShahGCapHouse/1.0"
        }
    )

    try:
        with urllib.request.urlopen(req, timeout=8) as response:
            print(f"✅ Email successfully delivered to {recipient_email} via Resend API (HTTP {response.status})")
    except Exception as e:
        print(f"⚠️ Resend API delivery error: {e}")


def send_order_notification_email(order):
    """
    Spawns a fast background thread to deliver the order alert to Mashood.
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

        # ⚡ Background Thread (Zero customer wait time)
        email_thread = threading.Thread(
            target=_send_email_via_resend_api,
            args=(subject, message, 'mashoodarshad22@gmail.com'),
            daemon=True
        )
        email_thread.start()

    except Exception as e:
        print(f"⚠️ Email preparation failed: {e}")


def checkout(request):
    """
    Handles checkout form display and secure Cash on Delivery order creation.
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
            try:
                with transaction.atomic():
                    if not request.session.session_key:
                        request.session.save()

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

                    order.total_cost = order_total + shipping_cost
                    order.save()

                # Clear session cart
                cart.clear()

                # Send fast HTTPS email notification
                send_order_notification_email(order)

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