from django.db import models
from products.models import ProductVariant # MODIFIED
from accounts.models import Address # MODIFIED: App name is accounts
import uuid
from django.contrib.auth import get_user_model # IMPORTED AS REQUESTED

User = get_user_model() # USED AS REQUESTED

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
    PAYMENT_STATUS = [
        ("pending", "Pending"),       # Awaiting payment
        ("completed", "Completed"),   # Payment successful
        ("failed", "Failed"),         # Payment failed
        ("refunded", "Refunded"),     # Payment was refunded
    ]

    # Core Order Details
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE, # If user is deleted, delete their orders
        related_name="orders"
    )
    order_number = models.CharField(
        max_length=20,
        unique=True,
        editable=False,
        help_text="Unique, human-readable order identifier."
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
    payment_status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS,
        default="pending",
        help_text="The current payment status of the order."
    )
    payment_method = models.CharField(max_length=50, blank=True)

    # --- Linked Address (Historical Reference) ---
    # These link to the Address model at the time of purchase.
    # We also store a snapshot (below) in case the user deletes the Address entry.
    shipping_address_link = models.ForeignKey(
        Address,
        on_delete=models.SET_NULL, # Keep order history even if address is deleted
        null=True,
        blank=True,
        related_name="shipping_orders",
        help_text="Link to the user's Address book entry (if available)."
    )
    billing_address_link = models.ForeignKey(
        Address,
        on_delete=models.SET_NULL, # Keep order history even if address is deleted
        null=True,
        blank=True,
        related_name="billing_orders",
        help_text="Link to the user's billing address entry (if available)."
    )
    # ------------------------------------------

    # --- Address Snapshot (Permanent Record) ---
    # These fields store the *actual* address used for shipping,
    # ensuring the order retains this info even if the user
    # updates or deletes their Address book entry.
    shipping_full_name = models.CharField(max_length=200, help_text="Snapshot of recipient's full name.")
    shipping_email = models.EmailField(help_text="Snapshot of recipient's email.")
    shipping_phone = models.CharField(max_length=20, help_text="Snapshot of recipient's phone.")
    shipping_address = models.TextField(help_text="Snapshot of recipient's street address.")
    shipping_city = models.CharField(max_length=100, help_text="Snapshot of recipient's city.")
    shipping_state = models.CharField(max_length=100, help_text="Snapshot of recipient's state.")
    shipping_zip = models.CharField(max_length=20, help_text="Snapshot of recipient's zip code.")
    shipping_country = models.CharField(max_length=100, default="USA", help_text="Snapshot of recipient's country.")
    # -------------------------------------------

    # Tracking
    tracking_number = models.CharField(
        max_length=100,
        blank=True,
        help_text="Shipping carrier's tracking number."
    )

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

    def save(self, *args, **kwargs):
        """
        Generates a unique order number on first save.
        """
        if not self.order_number:
            # Generates a random 8-char hex string
            self.order_number = f"ORD-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)

class OrderItem(models.Model):
    """
    Represents a single line item within an Order.

    This links a specific ProductVariant to the order and stores
    the quantity and price at the time of purchase.
    """
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey("products.Product", on_delete=models.CASCADE, null=True, blank=True)
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

    def get_subtotal(self):
        """
Async function to calculate the subtotal for this line item.
        """
        return self.price * self.quantity

