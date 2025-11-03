from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings
from products.models import Product, ProductVariant

# Note: We use string references ("products.Category", "products.Product")
# to prevent circular import errors, which is a Django best practice.


class User(AbstractUser):
    """
    Custom User model extending Django's AbstractUser.

    This model serves as the central point for all user-related data,
    including demographics, preferences, and app-specific settings.
    """

    ROLE_CHOICES = [
        ('customer', 'Customer'),
        ('staff', 'Staff'),
        ('admin', 'Admin'),
    ]
    
    # --- Demographic Fields (for personalization) ---
    age_range = models.CharField(max_length=50, null=True, blank=True)
    gender = models.CharField(max_length=50, null=True, blank=True)
    employment = models.CharField(max_length=100, null=True, blank=True)
    income_range = models.CharField(max_length=100, null=True, blank=True)

    # --- Core Account Fields ---
    role = models.CharField(
        max_length=50,
        choices=ROLE_CHOICES,
        default="customer",
        help_text="User role (e.g., customer, admin).",
    )
    email = models.EmailField(
        unique=True, help_text="Required. Used for login and communication."
    )
    first_name = models.CharField(max_length=150, blank=False)
    last_name = models.CharField(max_length=150, blank=False)

    # --- User Preferences ---
    preferred_category = models.ForeignKey(
        "products.Category",
        on_delete=models.SET_NULL,  # Keep user if category is deleted
        null=True,
        blank=True,
        related_name="preferred_by_users",
        help_text="User's preferred category for personalization.",
    )

    # --- Optional Profile Fields ---
    phone = models.CharField(max_length=20, blank=True, null=True)
    date_of_birth = models.DateField(null=True, blank=True)
    avatar = models.ImageField(upload_to="avatars/", null=True, blank=True)

    # --- Notification & Marketing Toggles (from ERD) ---
    allow_marketing_emails = models.BooleanField(
        default=False, help_text="User has opted-in to marketing communications."
    )
    allow_sale_notifications = models.BooleanField(
        default=False, help_text="User has opted-in to sale/stock alerts."
    )

    # --- Timestamps ---
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "users"
        verbose_name = "User"
        verbose_name_plural = "Users"

    def __str__(self):
        return self.username

    def get_full_name(self):
        """Returns the user's full name."""
        return f"{self.first_name} {self.last_name}".strip()

    def get_short_name(self):
        """Returns the user's first name."""
        return self.first_name


class Address(models.Model):
    """
    Stores a shipping or billing address for a user.
    A user can have multiple addresses.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,  # Best practice: links to User model in settings
        on_delete=models.CASCADE,  # If user is deleted, delete their addresses
        related_name="addresses",
    )
    full_name = models.CharField(max_length=255)
    address_type = models.CharField(max_length=20)
    address_line1 = models.CharField(
        max_length=255, help_text="Street address, P.O. box, etc."
    )
    address_line2 = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Apartment, suite, unit, etc. (Optional)",
    )
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100, help_text="State, province, or region.")
    postal_code = models.CharField(max_length=20, help_text="Postal code.", default='000000')
    zip_code = models.CharField(max_length=20)
    country = models.CharField(max_length=100, default="Singapore")
    is_default = models.BooleanField(
        default=False,
        help_text="Is this the default address for its type (shipping/billing)?",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Addresses"

    def __str__(self):
        return f"{self.full_name} - {self.address_line1}, {self.city}"

    def save(self, *args, **kwargs):
        """
        Ensures only one address of each type (shipping/billing)
        can be the default for a user.
        """
        if self.is_default:
            # Set all other addresses of this type for this user to non-default
            Address.objects.filter(
                user=self.user, address_type=self.address_type
            ).exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)


class Wishlist(models.Model):
    """
    Links a User to a ProductVariant they have "wishlisted".
    """

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='wishlist_items')
    product_variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE,  null=True, blank=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    added_at = models.DateTimeField(auto_now_add=True)  # NEW FIELD
    
    class Meta:
        unique_together = ('user', 'product_variant')
    
    def __str__(self):
        return f"{self.user.username} - {self.product_variant}"


class SaleSubscription(models.Model):
    """
    Tracks a user's request to be notified when a specific
    ProductVariant goes on sale.
    """

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sale_subscriptions')
    product_variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE)
    category = models.ForeignKey('products.Category', on_delete=models.CASCADE, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    subscribed_at = models.DateTimeField(auto_now_add=True)  # NEW FIELD
    is_active = models.BooleanField(default=True)
    
    class Meta:
        unique_together = ('user', 'product_variant')
    
    def __str__(self):
        return f"{self.user.username} - {self.product_variant}"


class BrowsingHistory(models.Model):
    """
    Logs products a user has viewed.
    Used for the "Personalized Recommendations" feature.
    """

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='browsing_history')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='browsing_history')
    viewed_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name_plural = 'Browsing Histories'
        ordering = ['-viewed_at']

    def __str__(self):
        return f"{self.user.username} viewed {self.product.name}"


class ChatConversation(models.Model):
    """
    Represents a single conversation thread between a user and an admin,
    usually regarding a specific product.
    """

    MESSAGE_TYPE_CHOICES = [
        ('contact_us', 'Contact Us'),
        ('product_chat', 'Product Chat'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('replied', 'Replied'),
    ]
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='conversations')
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True, related_name='chats')
    admin = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_chats')
    
    # NEW FIELDS
    subject = models.CharField(max_length=200, default='General Inquiry')
    message_type = models.CharField(max_length=20, choices=MESSAGE_TYPE_CHOICES, default='contact_us')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    user_has_unread = models.BooleanField(default=False)
    admin_has_unread = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return f"{self.user.username} - {self.subject}"


class ChatMessage(models.Model):
    """
    An individual message within a ChatConversation.
    """

    conversation = models.ForeignKey(ChatConversation, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.sender.username}: {self.content[:50]}"
