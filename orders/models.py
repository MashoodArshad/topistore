import uuid
from django.db import models
from django.contrib.auth.models import User
from products.models import Product


class Order(models.Model):
    """
    Core Order model with decoupled fulfillment and payment lifecycles.
    """
    
    # Fulfillment Status
    STATUS_CHOICES = [
        ('Pending', 'Pending (Awaiting Payment / Processing)'),
        ('Confirmed', 'Confirmed / Processing'),
        ('Shipped', 'Shipped'),
        ('Delivered', 'Delivered'),
        ('Canceled', 'Canceled'),
    ]

    # Payment Method Choices
    PAYMENT_METHOD_CHOICES = [
        ('ONLINE', 'Online Payment (Safepay: Cards / JazzCash / Easypaisa)'),
    ]

    # Payment Lifecycle Statuses
    PAYMENT_STATUS_CHOICES = [
        ('UNPAID', 'Unpaid / Awaiting Payment'),
        ('PROCESSING', 'Processing with Payment Gateway'),
        ('PAID', 'Paid & Verified'),
        ('FAILED', 'Payment Failed'),
        ('CANCELLED', 'Payment Cancelled by Customer'),
        ('REFUNDED', 'Refunded'),
    ]

    # Unique Human-Readable Order Reference (e.g. SGC-2025-A3F8)
    order_number = models.CharField(
        max_length=50,
        unique=True,
        blank=True,
        null=True,
        verbose_name="Order Reference"
    )

    # Customer Account & Contact Details
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='orders',
        verbose_name="Customer Account"
    )
    first_name = models.CharField(max_length=150, verbose_name="Full Name")
    phone = models.CharField(max_length=20, verbose_name="Phone / WhatsApp Number")
    address = models.TextField(verbose_name="Complete Shipping Address")
    city = models.CharField(max_length=100, verbose_name="City")

    # Financial Fields (Always computed server-side)
    shipping_cost = models.DecimalField(max_digits=10, decimal_places=2, default=150.00)
    total_cost = models.DecimalField(max_digits=10, decimal_places=2, help_text="Grand total including shipping")

    # Payment Gateway Metadata
    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES,
        default='ONLINE'
    )
    payment_status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default='UNPAID',
        db_index=True
    )
    tracker_token = models.CharField(
        max_length=150,
        blank=True,
        null=True,
        help_text="Official Safepay Order Tracker Token (track_...)"
    )
    payment_id = models.CharField(
        max_length=150,
        blank=True,
        null=True,
        help_text="Gateway Transaction Reference / Receipt ID"
    )
    paid_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when payment was cryptographically verified"
    )

    # Order Lifecycle & Auditing
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    session_key = models.CharField(max_length=40, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Customer Order'
        verbose_name_plural = 'Customer Orders'

    def __str__(self):
        ref = self.order_number or f"Order #{self.id}"
        return f"{ref} — {self.first_name} [{self.payment_status}]"

    def save(self, *args, **kwargs):
        """Auto-generate unique order reference before initial persistence."""
        if not self.order_number:
            short_id = uuid.uuid4().hex[:6].upper()
            self.order_number = f"SGC-2025-{short_id}"
        super().save(*args, **kwargs)


class OrderItem(models.Model):
    """
    Junction table recording products inside an order at historical purchasing price.
    """
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='order_items')
    price = models.DecimalField(max_digits=10, decimal_places=2, help_text="Unit price at checkout time")
    quantity = models.PositiveIntegerField(default=1)

    def __str__(self):
        ref = self.order.order_number or f"Order #{self.order.id}"
        return f"{self.quantity}x {self.product.name} ({ref})"

    def get_cost(self):
        return self.price * self.quantity