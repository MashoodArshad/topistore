from django.contrib import admin
from .models import Order, OrderItem


class OrderItemInline(admin.TabularInline):
    """
    Allows viewing and managing ordered articles directly inside the main Order view.
    """
    model = OrderItem
    raw_id_fields = ['product']
    extra = 0


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    """
    Admin layout for managing customer orders and delivery updates.
    """
    list_display = [
        'id', 
        'first_name', 
        'phone', 
        'city', 
        'total_cost', 
        'status', 
        'created_at'
    ]
    list_filter = ['status', 'created_at', 'city']
    list_editable = ['status']
    search_fields = ['first_name', 'phone', 'address', 'city']
    inlines = [OrderItemInline]
    ordering = ['-created_at']