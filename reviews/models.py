from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator


class Review(models.Model):
    """
    Product reviews.
    Moved to separate app to break circular dependency between accounts and products.
    """

    product = models.ForeignKey(
        'products.Product', on_delete=models.CASCADE, related_name="reviews"
    )
   
    # Use string reference to Customer to avoid circular dependency
    # Reviews are from customers, not staff or superusers
    # Since Review is in a separate app, this breaks the circular dependency:
    # accounts → products (Wishlist references Product)
    # reviews → accounts (Review references Customer)
    # reviews → products (Review references Product)
    # No cycle!
    user = models.ForeignKey(
        'accounts.Customer',
        on_delete=models.CASCADE,
    )
    rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    title = models.CharField(max_length=200)
    comment = models.TextField()
    is_verified_purchase = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        unique_together = ("product", "user")

    def __str__(self):
        return f"{self.product.name} - {self.rating}★"
