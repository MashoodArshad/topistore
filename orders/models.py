from django.db import models
from products.models import Product


class Order(models.Model):
    """
    Model storing customer delivery details and order metadata.
    """
    STATUS_CHOICES = [
        ('Pending', 'Pending (Unconfirmed)'),
        ('Confirmed', 'Confirmed / Processing'),
        ('Shipped', 'Shipped'),
        ('Delivered', 'Delivered'),
        ('Canceled', 'Canceled'),
    ]

    first_name = models.CharField(max_length=150, verbose_name="Full Name")
    phone = models.CharField(max_length=20, verbose_name="Phone / WhatsApp Number")
    address = models.TextField(verbose_name="Complete Shipping Address")
    city = models.CharField(max_length=100, verbose_name="City")
    
    # Financial fields
    shipping_cost = models.DecimalField(max_digits=10, decimal_places=2, default=150.00)
    total_cost = models.DecimalField(max_digits=10, decimal_places=2, help_text="Grand total including shipping")
    
    # Internal order tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Customer Order'
        verbose_name_plural = 'Customer Orders'

    def __str__(self):
        return f"Order #{self.id} — {self.first_name} ({self.city})"


class OrderItem(models.Model):
    """
    Junction table storing specific products bought inside an order.
    """
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='order_items')
    price = models.DecimalField(max_digits=10, decimal_places=2, help_text="Price of item at the time of purchase")
    quantity = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.quantity}x {self.product.name} (Order #{self.order.id})"

    def get_cost(self):
        return self.price * self.quantity