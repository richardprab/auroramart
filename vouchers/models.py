from django.db import models
from django.conf import settings


class Voucher(models.Model):
    """
    Industry-standard voucher model with comprehensive features.
    Supports fixed amount, percentage discounts, usage limits, and more.
    """
    DISCOUNT_TYPE_CHOICES = [
        ('percent', 'Percentage'),  # A percentage off the total
        ('fixed', 'Fixed Amount'),  # A fixed amount off the total
        ('free_shipping', 'Free Shipping'),  # Free shipping voucher
    ]

    # Basic Information
    name = models.CharField(
        max_length=255, 
        help_text="Internal name for the voucher."
    )
    promo_code = models.CharField(
        max_length=100,
        unique=True,
        help_text="The code customers enter. Must be unique and uppercase."
    )
    description = models.TextField(
        null=True, 
        blank=True,
        help_text="Public description shown to customers."
    )
    
    # Discount Configuration
    discount_type = models.CharField(
        max_length=20,
        choices=DISCOUNT_TYPE_CHOICES,
        default='percent',
        help_text="Type of discount to apply."
    )
    discount_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="The value of the discount (e.g., 10 for 10% or 10.00 for $10)."
    )
    max_discount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Maximum discount amount (for percentage discounts). Leave blank for no limit."
    )
    
    # Eligibility Requirements
    min_purchase = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Minimum cart subtotal required to use this voucher."
    )
    first_time_only = models.BooleanField(
        default=False,
        help_text="If True, only users with no previous orders can use this voucher."
    )
    
    # Product/Category Restrictions
    applicable_categories = models.ManyToManyField(
        'products.Category',
        blank=True,
        help_text="If selected, voucher only applies to products in these categories. Leave empty for all products."
    )
    applicable_products = models.ManyToManyField(
        'products.Product',
        blank=True,
        help_text="If selected, voucher only applies to these specific products. Leave empty for all products."
    )
    exclude_sale_items = models.BooleanField(
        default=False,
        help_text="If True, voucher cannot be used on items already on sale."
    )
    
    # Usage Limits
    max_uses = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Maximum number of times this voucher can be used in total. Leave blank for unlimited."
    )
    max_uses_per_user = models.PositiveIntegerField(
        default=1,
        help_text="Maximum number of times a single user can use this voucher."
    )
    current_uses = models.PositiveIntegerField(
        default=0,
        help_text="Current number of times this voucher has been used."
    )
    
    # User Restrictions
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='vouchers',
        help_text="If set, only this specific customer can use this voucher. Leave blank for public use."
    )
    
    # Validity Period
    start_date = models.DateTimeField(
        help_text="Date and time when the voucher becomes valid."
    )
    end_date = models.DateTimeField(
        help_text="Date and time when the voucher expires."
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether the voucher is currently active. Inactive vouchers cannot be used."
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_vouchers',
        help_text="Admin user who created this voucher."
    )

    class Meta:
        db_table = "vouchers"
        ordering = ['-created_at']
        verbose_name = "Voucher"
        verbose_name_plural = "Vouchers"

    def __str__(self):
        return f"{self.name} ({self.promo_code})"

    def save(self, *args, **kwargs):
        """Ensure promo code is uppercase for consistency."""
        if self.promo_code:
            self.promo_code = self.promo_code.upper().strip()
        super().save(*args, **kwargs)

    def is_valid(self):
        """Check if voucher is currently valid (active and within date range)."""
        from django.utils import timezone
        now = timezone.now()
        return (
            self.is_active and
            self.start_date <= now <= self.end_date
        )

    def can_be_used_by_user(self, user, usage_count=None):
        """
        Check if a specific user can use this voucher.
        
        Args:
            user: User to check
            usage_count: Optional pre-calculated usage count to avoid duplicate query
        """
        # Check if voucher is user-specific
        if self.user and self.user != user:
            return False
        
        # Check first-time user restriction
        if self.first_time_only:
            from orders.models import Order
            if Order.objects.filter(user=user).exists():
                return False
        
        # Check per-user usage limit
        if usage_count is None:
            usage_count = VoucherUsage.objects.filter(
                voucher=self,
                user=user
            ).count()
        if usage_count >= self.max_uses_per_user:
            return False
        
        return True

    def is_usage_limit_reached(self):
        """Check if total usage limit has been reached."""
        if self.max_uses is None:
            return False
        return self.current_uses >= self.max_uses


class VoucherUsage(models.Model):
    """
    Tracks individual voucher usage instances.
    Prevents duplicate usage and provides audit trail.
    """
    voucher = models.ForeignKey(
        Voucher,
        on_delete=models.CASCADE,
        related_name='usages'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='voucher_usages'
    )
    order = models.ForeignKey(
        'orders.Order',
        on_delete=models.CASCADE,
        related_name='voucher_usage',
        null=True,
        blank=True
    )
    discount_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="The actual discount amount applied in this usage."
    )
    used_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "voucher_usages"
        ordering = ['-used_at']
        unique_together = [['voucher', 'order']]  # Prevent duplicate usage per order
        verbose_name = "Voucher Usage"
        verbose_name_plural = "Voucher Usages"

    def __str__(self):
        return f"{self.user.username} used {self.voucher.promo_code} on {self.used_at.date()}"

