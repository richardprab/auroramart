from django.db import models
from accounts.models import Address
from django.conf import settings
from datetime import timedelta
from django.utils import timezone
import uuid
import random

class Order(models.Model):
    """
    Represents a customer's completed order.

    This model stores all information related to a purchase, including
    the user, payment details, pricing breakdown, and a snapshot
    of the shipping address at the time of purchase.
    """
    STATUS_CHOICES = [
        ("pending", "Pending"),       # Order received, awaiting payment or confirmation
        ("confirmed", "Confirmed"),   # Payment received, awaiting processing
        ("processing", "Processing"), # Order is being prepared for shipment
        ("shipped", "Shipped"),       # Order has been handed to the carrier
        ("delivered", "Delivered"),   # Order has been delivered to the customer
        ("cancelled", "Cancelled"),   # Order was cancelled by user or admin
        ("refunded", "Refunded"),     # Order was refunded
    ]
    
    LOCATION_CHOICES = [
        ('warehouse', 'Warehouse'),
        ('in_transit_dc', 'In Transit to Distribution Center'),
        ('at_dc', 'At Distribution Center'),
        ('out_delivery', 'Out for Delivery'),
        ('delivered', 'Delivered'),
    ]

    order_number = models.CharField(
        max_length=20, 
        unique=True, 
        blank=True,
        help_text="Unique order number (auto-generated)"
    )

    # Core Order Details
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE, # If user is deleted, delete their orders
        related_name="orders"
    )
    address = models.ForeignKey(Address, on_delete=models.SET_NULL, null=True)
    delivery_address = models.TextField(
        blank=True,
        help_text="Snapshot of delivery address at time of order (for historical reference)."
    )
    
    # Pricing Breakdown
    subtotal = models.DecimalField(
        max_digits=10, decimal_places=2,
        help_text="Total price of items before tax and shipping."
    )
    tax = models.DecimalField(
        max_digits=10, decimal_places=2,
        default=0,
        help_text="Tax amount charged."
    )
    shipping_cost = models.DecimalField(
        max_digits=10, decimal_places=2,
        default=0,
        help_text="Shipping cost charged."
    )
    total = models.DecimalField(
        max_digits=10, decimal_places=2,
        help_text="The final amount charged to the customer (subtotal + tax + shipping)."
    )

    # Order Status
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending",
        help_text="The current fulfillment status of the order."
    )

    payment_status = models.CharField(max_length=20, blank=True)

    payment_method = models.CharField(max_length=50, blank=True)
    current_location = models.CharField(max_length=50, choices=LOCATION_CHOICES, default='warehouse')
    
    # Contact information
    contact_number = models.CharField(max_length=20, blank=True)
    
    # Delivery tracking
    tracking_number = models.CharField(
        max_length=100,
        blank=True,
        help_text="Shipping carrier's tracking number."
    )
    expected_delivery_date = models.DateField(null=True, blank=True)
    
    # Notes
    customer_notes = models.TextField(blank=True, help_text="Any notes the customer left during checkout.")
    admin_notes = models.TextField(blank=True, help_text="Internal notes for admins.")

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    paid_at = models.DateTimeField(null=True, blank=True, help_text="Timestamp when payment was completed.")
    shipped_at = models.DateTimeField(null=True, blank=True, help_text="Timestamp when order was shipped.")
    delivered_at = models.DateTimeField(null=True, blank=True, help_text="Timestamp when order was delivered.")

    class Meta:
        ordering = ["-created_at"] # Show newest orders first

    def __str__(self):
        return f"Order {self.order_number}"

    @property
    def total_item_quantity(self):
        """Calculate the total quantity of all items in the order."""
        return sum(item.quantity for item in self.items.all())

    def save(self, *args, **kwargs):
        """
        Generates a unique order number on first save.
        """
        if not self.order_number:
            # Generates a random 8-char hex string
            self.order_number = f"ORD-{uuid.uuid4().hex[:8].upper()}"
        # Auto-generate expected delivery date if not set
        if not self.expected_delivery_date and self.status in ['confirmed', 'processing']:
            days_to_deliver = random.randint(3, 7)
            self.expected_delivery_date = timezone.now().date() + timedelta(days=days_to_deliver)
        super().save(*args, **kwargs)

class OrderItem(models.Model):
    """
    Represents a single line item within an Order.

    This links a specific ProductVariant to the order and stores
    the quantity and price at the time of purchase.
    """
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey("products.Product", on_delete=models.CASCADE, null=True, blank=True, help_text="Product reference (can be derived from variant)")
    product_variant = models.ForeignKey("products.ProductVariant", on_delete=models.CASCADE, null=True, blank=True, related_name="order_items")
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(
        max_digits=10, decimal_places=2,
        help_text="Price of the product *at the time of purchase*."
    )
    
    def __str__(self):
        """
        Provides a human-readable representation of the order item.
        Includes a try-except block to prevent errors if the related
        product_variant has been deleted (despite PROTECT).
        """
        try:
            return f"{self.quantity}x {self.product_variant.sku}"
        except Exception:
            return f"Order item {self.id} (Product Variant missing)"

    @property
    def subtotal(self):
        return self.quantity * self.price

