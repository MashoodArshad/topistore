from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from cart.cart import Cart
from .models import Order, OrderItem


def send_order_notification_email(order):
    """
    Sends an automated instant email alert to the business owner (Mashood).
    """
    try:
        items_list = ""
        for item in order.items.all():
            items_list += f"- {item.quantity}x {item.product.name} (Rs. {item.get_cost():,.0f})\n"

        subject = f"🚨 New Order #{order.id} Received — Shah G Cap House"
        message = f"""
Assalamu Alaikum Mashood,

You have received a new order on Shah G Cap House!

========================================
ORDER DETAILS (Order #{order.id})
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

Please contact the customer on WhatsApp ({order.phone}) to confirm the dispatch.
        """

        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=['mashoodarshad22@gmail.com'],
            fail_silently=False,
        )
    except Exception as e:
        # Prevent checkout crash if email service is temporarily unreachable
        print(f"⚠️ Email notification failed: {e}")


def checkout(request):
    """
    Handles checkout form display and Cash on Delivery order creation.
    """
    cart = Cart(request)

    if len(cart) == 0:
        messages.warning(request, "Your shopping bag is empty. Please select an article first.")
        return redirect('cart:cart_detail')

    subtotal = cart.get_subtotal_price()
    shipping_cost = 0 if subtotal >= 5000 else 150
    grand_total = subtotal + shipping_cost

    if request.method == 'POST':
        first_name = request.POST.get('first_name', '').strip()
        phone = request.POST.get('phone', '').strip()
        address = request.POST.get('address', '').strip()
        city = request.POST.get('city', '').strip()

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
            product = item['product']
            product.stock = max(0, product.stock - item['quantity'])
            product.save()

        # 3. Clear shopping session cart
        cart.clear()

        # 4. Trigger Instant Email Notification to Business Owner
        send_order_notification_email(order)

        # 5. Redirect to Order Success Page
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
    Renders order confirmation screen with 1-Click WhatsApp Connect button.
    """
    order = get_object_or_404(Order, id=order_id)
    return render(request, 'orders/order_success.html', {'order': order})