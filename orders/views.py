import os
import json
import traceback
import urllib.request
import threading
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import transaction
from django.contrib.auth.decorators import login_required
from cart.cart import Cart
from payments.gateway import SafepayGatewayClient
from .models import Order, OrderItem
from .forms import OrderCreateForm


def _send_email_via_resend_api(subject, message_text, recipient_email):
    """Sends fast transactional email via Resend API."""
    api_key = os.getenv('RESEND_API_KEY', '').strip()
    if not api_key:
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
            print(f"✅ Email delivered to {recipient_email}")
    except Exception as e:
        print(f"⚠️ Email dispatch error: {e}")


def send_order_notification_email(order):
    """Fires background thread to notify store owner of verified paid order."""
    try:
        items_list = ""
        for item in order.items.all():
            items_list += f"- {item.quantity}x {item.product.name} (Rs. {item.get_cost():,.0f})\n"

        ref = order.order_number or f"Order #{order.id}"
        subject = f"🚨 VERIFIED PAID ORDER {ref} — Shah G Cap House"
        message = f"""
Assalamu Alaikum Mashood,

You have received a new VERIFIED PAID order on Shah G Cap House!

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
Grand Total Paid: Rs. {order.total_cost:,.0f}
Payment Method: Safepay (Cards / JazzCash / Easypaisa)
Payment Status: {order.payment_status}
Gateway Reference: {order.payment_id or order.tracker_token}

========================================
TIMESTAMP: {order.created_at.strftime('%d %B %Y, %I:%M %p')}

This order has been verified. Dispatch parcel to customer.
        """

        email_thread = threading.Thread(
            target=_send_email_via_resend_api,
            args=(subject, message, 'mashoodarshad22@gmail.com'),
            daemon=True
        )
        email_thread.start()

    except Exception as e:
        print(f"⚠️ Email notification preparation error: {e}")


@login_required
def checkout(request):
    """
    Handles checkout form validation, creates UNPAID Order,
    initializes Safepay payment session, and redirects to Safepay Hosted Portal.
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
            order = None
            try:
                # 1. Create UNPAID Order in Database
                with transaction.atomic():
                    order = Order.objects.create(
                        user=request.user,
                        first_name=form.cleaned_data['first_name'],
                        phone=form.cleaned_data['phone'],
                        address=form.cleaned_data['address'],
                        city=form.cleaned_data['city'],
                        shipping_cost=shipping_cost,
                        total_cost=grand_total_display,
                        payment_method='ONLINE',
                        payment_status='UNPAID',
                        status='Pending',
                    )

                    for item in cart:
                        db_product = item['product']
                        OrderItem.objects.create(
                            order=order,
                            product=db_product,
                            price=db_product.price,
                            quantity=item['quantity']
                        )

                # 2. Call Official Safepay API to create session token
                gateway = SafepayGatewayClient()
                tracker_token, error_msg = gateway.create_order_tracker(order)

                if tracker_token:
                    order.tracker_token = tracker_token
                    order.payment_status = 'PROCESSING'
                    order.save(update_fields=['tracker_token', 'payment_status'])

                    # 3. Construct Hosted Gateway URL
                    redirect_url = request.build_absolute_uri(f'/payments/callback/{order.order_number}/')
                    cancel_url = request.build_absolute_uri(f'/payments/cancel/{order.order_number}/')
                    
                    checkout_url = gateway.construct_checkout_url(
                        tracker_token=tracker_token,
                        order=order,
                        redirect_url=redirect_url,
                        cancel_url=cancel_url
                    )

                    # 4. Redirect customer to Official Safepay Hosted Portal
                    return redirect(checkout_url)

                else:
                    if order:
                        order.delete()
                    messages.error(request, f"Safepay Gateway Error: {error_msg}")

            except Exception as e:
                print(f"⚠️ Checkout Detailed Error: {traceback.format_exc()}")
                if order and order.id:
                    order.delete()
                messages.error(request, f"Gateway Connection Error: {str(e)}")
        else:
            messages.error(request, "Please correct the errors in the form below.")
    else:
        # Pre-fill user details
        user_fullname = f"{request.user.first_name} {request.user.last_name}".strip() or request.user.username
        user_phone = request.user.profile.phone if hasattr(request.user, 'profile') else ""
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


@login_required
def order_success(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    return render(request, 'orders/order_success.html', {'order': order})


@login_required
def order_history(request):
    orders = Order.objects.filter(user=request.user)
    return render(request, 'orders/order_history.html', {'orders': orders})


@login_required
def order_detail(request, order_number):
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    return render(request, 'orders/order_detail.html', {'order': order})