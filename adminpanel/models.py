from django.db import models
from django.contrib.auth import get_user_model # IMPORTED AS REQUESTED

User = get_user_model() # USED AS REQUESTED

class HomepageBanner(models.Model):
    """
    Model for admin-controlled homepage banners, pop-ups,
    or promotional content.
    """
    title = models.CharField(max_length=255)
    message = models.TextField(help_text="The main content of the banner/pop-up.")
    link = models.URLField(
        max_length=1024,
        null=True,
        blank=True,
        help_text="An optional URL to link to (e.g., /sale/summer-sale)."
    )
    is_active = models.BooleanField(
        default=False,
        help_text="Only active banners will be shown on the site."
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} ({'Active' if self.is_active else 'Inactive'})"

class Coupon(models.Model):
    """
    Model for coupons and promo codes.
    Can be public (promo code) or private (linked to a user).
    """
    DISCOUNT_TYPE_CHOICES = [
        ('percent', 'Percentage'),  # A percentage off the total
        ('fixed', 'Fixed Amount'),  # A fixed amount off the total
    ]

    name = models.CharField(max_length=255, help_text="Internal name for the coupon.")
    promo_code = models.CharField(
        max_length=100,
        unique=True,
        null=True,
        blank=True,
        help_text="The code customers enter (if public)."
    )
    description = models.TextField(null=True, blank=True)
    discount_type = models.CharField(
        max_length=10,
        choices=DISCOUNT_TYPE_CHOICES,
        default='percent'
    )
    discount_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="The value of the discount (e.g., 10 for 10% or 10.00 for $10)."
    )
    min_purchase = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="The minimum cart total required to use this coupon."
    )
    
    # --- MODIFIED: Using get_user_model() as requested ---
    user = models.ForeignKey(
        User, # This now refers to User = get_user_model()
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        help_text="If null, coupon is public. If set, only this user can use it."
    )
    # -----------------------------------------------------

    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    is_active = models.BooleanField(
        default=True,
        help_text="Whether the coupon is currently valid."
    )

    def __str__(self):
        return f"{self.name} ({self.promo_code})"


