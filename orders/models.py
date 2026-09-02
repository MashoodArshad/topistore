import uuid
from django.db import models
from django.contrib.auth.models import User  # 👈 1. Django ka User Model import kiya
from products.models import Product


class Order(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending (Unconfirmed)'),
        ('Confirmed', 'Confirmed / Processing'),
        ('Shipped', 'Shipped'),
        ('Delivered', 'Delivered'),
        ('Canceled', 'Canceled'),
    ]

    # Unique human-readable order number
    order_number = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name="Order Reference"
    )

    # 👈 2. Order ko User account ke sath link kar diya (1 User has many Orders)
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

    # Financial fields
    shipping_cost = models.DecimalField(max_digits=10, decimal_places=2, default=150.00)
    total_cost = models.DecimalField(max_digits=10, decimal_places=2, help_text="Grand total including shipping")

    # Internal order tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    session_key = models.CharField(max_length=40, blank=True, null=True, help_text="For guest order history fallback")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Customer Order'
        verbose_name_plural = 'Customer Orders'

    def __str__(self):
        ref = self.order_number or f"Order #{self.id}"
        return f"{ref} — {self.first_name} ({self.city})"

    def save(self, *args, **kwargs):
        """Auto-generate unique order number before saving."""
        if not self.order_number:
            short_id = uuid.uuid4().hex[:6].upper()
            self.order_number = f"SGC-2025-{short_id}"
        super().save(*args, **kwargs)


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='order_items')
    price = models.DecimalField(max_digits=10, decimal_places=2, help_text="Price at time of purchase (from DB)")
    quantity = models.PositiveIntegerField(default=1)

    def __str__(self):
        ref = self.order.order_number or f"Order #{self.order.id}"
        return f"{self.quantity}x {self.product.name} ({ref})"

    def get_cost(self):
        return self.price * self.quantity