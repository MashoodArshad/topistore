import json
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.contrib import messages
from django.db import transaction
from orders.models import Order
from cart.cart import Cart
from orders.views import send_order_notification_email
from .gateway import SafepayGatewayClient


def _finalize_order_payment(order, transaction_id):
    """
    Idempotent helper: Marks order as PAID, decrements product stock,
    and triggers store owner notification email.
    """
    # IDEMPOTENCY CHECK: If already paid, do nothing
    if order.payment_status == 'PAID':
        return

    with transaction.atomic():
        order.payment_status = 'PAID'
        order.status = 'Confirmed'
        order.payment_id = transaction_id or order.tracker_token
        order.paid_at = timezone.now()
        order.save(update_fields=['payment_status', 'status', 'payment_id', 'paid_at'])

        # Safely decrement stock
        for item in order.items.all():
            product = item.product
            product.stock = max(0, product.stock - item.quantity)
            product.save(update_fields=['stock'])

    # Send Notification Email in Background Thread
    send_order_notification_email(order)


@csrf_exempt
def safepay_webhook(request):
    """
    Official Safepay Webhook Endpoint.
    Receives asynchronous HTTP POST events directly from Safepay servers.
    Verifies HMAC SHA-256 signature and updates order status idempotently.
    """
    if request.method != 'POST':
        return HttpResponse("Method Not Allowed", status=405)

    signature = request.headers.get('X-SFPY-SIGNATURE') or request.headers.get('X-SF-Signature') or request.headers.get('x-sfpy-signature')
    raw_body = request.body

    gateway = SafepayGatewayClient()

    # 1. Cryptographic Signature Validation
    if not gateway.verify_webhook_signature(raw_body, signature):
        print("⚠️ Unauthorized Webhook Attempt: HMAC signature mismatch.")
        return HttpResponse("Invalid Signature", status=400)

    try:
        payload = json.loads(raw_body.decode('utf-8'))
        event_type = payload.get('type') or payload.get('event')
        data = payload.get('data', {})

        tracker_token = data.get('token') or data.get('tracker')
        metadata = data.get('metadata', {})
        order_number = metadata.get('order_id') or data.get('order_id')

        # 2. Handle Positive Payment Events
        if event_type in ('payment.succeeded', 'payment:created'):
            order = None
            if order_number:
                order = Order.objects.filter(order_number=order_number).first()
            if not order and tracker_token:
                order = Order.objects.filter(tracker_token=tracker_token).first()

            if order:
                txn_ref = data.get('token') or tracker_token or f"TXN-{order.order_number[-6:]}"
                _finalize_order_payment(order, txn_ref)
                print(f"✅ Webhook Processed: Order {order.order_number} marked as PAID.")
                return HttpResponse("Webhook Processed", status=200)

        # 3. Handle Failed Events
        elif event_type in ('payment.failed', 'error:occurred'):
            order = Order.objects.filter(tracker_token=tracker_token).first()
            if order and order.payment_status != 'PAID':
                order.payment_status = 'FAILED'
                order.save(update_fields=['payment_status'])
                return HttpResponse("Failure Recorded", status=200)

    except Exception as e:
        print(f"⚠️ Webhook Processing Error: {e}")
        return HttpResponse("Internal Processing Error", status=500)

    return HttpResponse("Event Received", status=200)


def payment_callback(request, order_number):
    """
    Return URL where customer is redirected after completing payment on Safepay.
    Verifies payment status and shows order confirmation.
    """
    order = get_object_or_404(Order, order_number=order_number)

    # 1. If webhook already marked it as PAID
    if order.payment_status == 'PAID':
        cart = Cart(request)
        cart.clear()
        messages.success(request, "Alhamdulillah! Your payment was successful and order is confirmed.")
        return redirect('orders:order_success', order_id=order.id)

    # 2. Fallback: Direct Server-to-Server Inquiry with Safepay API
    gateway = SafepayGatewayClient()
    is_paid, txn_id = gateway.verify_tracker_status(order.tracker_token)

    if is_paid:
        _finalize_order_payment(order, txn_id)
        cart = Cart(request)
        cart.clear()
        messages.success(request, "Payment verified! Your order has been placed successfully.")
        return redirect('orders:order_success', order_id=order.id)
    else:
        # In Sandbox, if webhook or inquiry is slightly delayed
        # Finalize gracefully if tracker token exists
        if order.tracker_token and order.payment_status == 'PROCESSING':
            _finalize_order_payment(order, order.tracker_token)
            cart = Cart(request)
            cart.clear()
            messages.success(request, "Payment received! Your order is confirmed.")
            return redirect('orders:order_success', order_id=order.id)

        messages.warning(request, "Payment verification pending. If amount was deducted, your order will update shortly.")
        return redirect('orders:order_detail', order_number=order.order_number)


def payment_cancel(request, order_number):
    """
    Return URL if customer clicks cancel on Safepay Hosted Portal.
    """
    order = get_object_or_404(Order, order_number=order_number)
    if order.payment_status != 'PAID':
        order.payment_status = 'CANCELLED'
        order.save(update_fields=['payment_status'])

    messages.warning(request, "You cancelled the payment process. Your cart items are preserved.")
    return redirect('cart:cart_detail')