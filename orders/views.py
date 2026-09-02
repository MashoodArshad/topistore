import os
import json
import urllib.request
import threading
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import transaction
from django.contrib.auth.decorators import login_required  # 👈 1. Import Login Required Guard
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


@login_required  # 👈 2. Guard Lagaya (Bina login ke is view mein koi nahi aa sakta)
def checkout(request):
    """
    Handles checkout form display and secure Cash on Delivery order creation.
    Requires user authentication, pre-fills billing details from profile.
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
                    # Order save karte waqt authenticated user details lock karein
                    order = Order(
                        user=request.user,  # 👈 3. Order ke user field ko lock kiya
                        first_name=form.cleaned_data['first_name'],
                        phone=form.cleaned_data['phone'],
                        address=form.cleaned_data['address'],
                        city=form.cleaned_data['city'],
                        shipping_cost=shipping_cost,
                        total_cost=0,
                        status='Pending',
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
        # 👈 4. FORM PRE-FILL: Database se authenticated user ka data uthaya
        user_fullname = f"{request.user.first_name} {request.user.last_name}".strip() or request.user.username
        user_phone = ""
        if hasattr(request.user, 'profile'):
            user_phone = request.user.profile.phone or ""

        # Pre-fill initial form fields
        form = OrderCreateForm(initial={
            'first_name': user_fullname,
            'phone': user_phone
        })

    context = {
        'form': form,
        'cart': cart,
        'subtotal': subtotal_display,
        'shipping_fee': shipping_cost,
        'grand_total': grand_total_display,
    }
    return render(request, 'orders/checkout.html', context)


@login_required  # Guard lagaya taake sirf orders place karne wala hi success page dekhe
def order_success(request, order_id):
    """
    Renders order confirmation screen with 1-Click WhatsApp Connect button.
    """
    order = get_object_or_404(Order, id=order_id, user=request.user) # 👈 5. Secure check (Koi aur na dekh sake)
    return render(request, 'orders/order_success.html', {'order': order})


@login_required  # Guard lagaya
def order_history(request):
    """
    Shows order history for the current logged-in user.
    """
    # 👈 6. Purana session system khatam, authenticated user ke direct orders get kiye
    orders = Order.objects.filter(user=request.user)
    return render(request, 'orders/order_history.html', {'orders': orders})


@login_required  # Guard lagaya
def order_detail(request, order_number):
    """
    Shows detailed view of a specific order for the customer.
    """
    # 👈 7. Security check: Sirf logged-in user apna order hi dekh sake
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    return render(request, 'orders/order_detail.html', {'order': order})