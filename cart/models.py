from django.db import models
from django.conf import settings
from products.models import Product


class Cart(models.Model):
    """Shopping cart model"""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="cart",
    )
    session_key = models.CharField(max_length=40, null=True, blank=True, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "cart"
        verbose_name = "Cart"
        verbose_name_plural = "Carts"

    def __str__(self):
        if self.user:
            return f"Cart for {self.user.username}"
        return f"Cart {self.session_key}"

    def get_total(self):
        """Calculate total cart value"""
        return sum(item.get_subtotal() for item in self.items.all())

    def get_item_count(self):
        """Get total number of items"""
        return sum(item.quantity for item in self.items.all())

    def clear(self):
        """Clear all items from cart"""
        self.items.all().delete()


class CartItem(models.Model):
    """Cart item model"""

    cart = models.ForeignKey(Cart, related_name="items", on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "cart_items"
        unique_together = ("cart", "product")
        ordering = ["-added_at"]
        verbose_name = "Cart Item"
        verbose_name_plural = "Cart Items"

    def __str__(self):
        return f"{self.quantity}x {self.product.name}"

    def get_subtotal(self):
        """Calculate subtotal for this cart item"""
        return self.product.price * self.quantity
