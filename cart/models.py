from django.db import models
from django.conf import settings
from products.models import ProductVariant # MODIFIED
from django.contrib.auth import get_user_model # IMPORTED AS REQUESTED

User = get_user_model() # USED AS REQUESTED

class Cart(models.Model):
    """
    Represents a shopping cart.

    A cart can be associated with a logged-in User or be
    an anonymous cart identified by a `session_key`.
    """
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE,
        null=True, # Allows for anonymous carts
        blank=True,
        related_name="cart",
    )

    session_key = models.CharField(
        max_length=40,
        null=True,
        blank=True,
        unique=True,
        help_text="Session key for anonymous user carts."
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "cart"
        verbose_name = "Cart"
        verbose_name_plural = "Carts"

    def __str__(self):
        if self.user:
            return f"Cart for {self.user.username}"
        return f"Anonymous Cart {self.session_key}"

    def get_total(self):
        """
        Calculates the total value of all items in the cart.
        """
        return sum(item.get_subtotal() for item in self.items.all())

    def get_item_count(self):
        """
        Calculates the total number of items (respecting quantity) in the cart.
        """
        return sum(item.quantity for item in self.items.all())

    def clear(self):
        """
        Removes all items from the cart.
        """
        self.items.all().delete()

class CartItem(models.Model):
    """
    Represents a single line item in a shopping cart,
    linking a specific `ProductVariant` to a `Cart`.
    """
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey("products.Product", on_delete=models.CASCADE, null=True, blank=True)
    product_variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, null=True, blank=True, related_name="cart_items")
    quantity = models.PositiveIntegerField(default=1)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "cart_items"
        unique_together = ("cart", "product_variant") # Can only add a variant once per cart
        ordering = ["-added_at"] # Show most recently added items first
        verbose_name = "Cart Item"
        verbose_name_plural = "Cart Items"

    def __str__(self):
        """
        Provides a human-readable representation of the cart item.
        Includes a try-except block to prevent errors if the related
        product_variant has been deleted.
        """
        try:
            return f"{self.quantity}x {self.product_variant.sku}"
        except Exception:
            return f"Cart item {self.id} (Variant missing)"

    def get_subtotal(self):
        """
        Calculates the subtotal for this line item.
        """
        try:
            return self.product_variant.price * self.quantity
        except Exception:
            return 0 # Or handle as appropriate

