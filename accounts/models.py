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

    # --- Demographic Fields (for personalization) ---
    age_range = models.CharField(max_length=50, null=True, blank=True)
    gender = models.CharField(max_length=50, null=True, blank=True)
    employment = models.CharField(max_length=100, null=True, blank=True)
    income_range = models.CharField(max_length=100, null=True, blank=True)

    # --- Core Account Fields ---
    role = models.CharField(
        max_length=50,
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

    ADDRESS_TYPES = [
        ("shipping", "Shipping"),
        ("billing", "Billing"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,  # Best practice: links to User model in settings
        on_delete=models.CASCADE,  # If user is deleted, delete their addresses
        related_name="addresses",
    )
    address_type = models.CharField(
        max_length=10, choices=ADDRESS_TYPES, default="shipping"
    )
    full_name = models.CharField(
        max_length=200, help_text="Full name of the recipient."
    )
    phone = models.CharField(max_length=20)
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
    zip_code = models.CharField(max_length=20, help_text="Postal code.")
    country = models.CharField(max_length=100, default="USA")
    is_default = models.BooleanField(
        default=False,
        help_text="Is this the default address for its type (shipping/billing)?",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Addresses"

    def __str__(self):
        return f"{self.get_address_type_display()} Address for {self.user.username}"

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

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="wishlists")
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="wishlists",
    )
    product_variant = models.ForeignKey(
        ProductVariant,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="wishlist_variants",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        if self.product_variant:
            return f"{self.user} - {self.product_variant}"
        elif self.product:
            return f"{self.user} - {self.product}"
        else:
            return f"{self.user} - Wishlist Item"

    class Meta:
        db_table = "wishlist"
        unique_together = (
            "user",
            "product_variant",
        )  # User can only wishlist a variant once
        ordering = ["-created_at"]


class SaleSubscription(models.Model):
    """
    Tracks a user's request to be notified when a specific
    ProductVariant goes on sale.
    """

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="sale_subscriptions"
    )
    product_variant = models.ForeignKey(
        "products.ProductVariant",
        on_delete=models.CASCADE,
        related_name="sale_subscriptions",
        help_text="The specific variant the user is watching.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = (
            "user",
            "product_variant",
        )  # User can only subscribe once per variant

    def __str__(self):
        try:
            return f"{self.user.username} subscribed to {self.product_variant.sku}"
        except Exception:
            return f"SaleSubscription item {self.id}"


class BrowsingHistory(models.Model):
    """
    Logs products a user has viewed.
    Used for the "Personalized Recommendations" feature.
    """

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="browsing_history"
    )
    product = models.ForeignKey(
        "products.Product",
        on_delete=models.CASCADE,
        related_name="viewed_by",
        help_text="The parent product the user viewed.",
    )
    viewed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-viewed_at"]  # Show most recent views first


class ChatConversation(models.Model):
    """
    Represents a single conversation thread between a user and an admin,
    usually regarding a specific product.
    """

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="chat_conversations"
    )
    product = models.ForeignKey(
        "products.Product",
        on_delete=models.CASCADE,
        related_name="chat_conversations",
        help_text="The product this chat is about.",
    )
    admin = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,  # Keep chat history if admin account is deleted
        null=True,
        blank=True,
        related_name="admin_chats",
        limit_choices_to={"is_staff": True},  # Ensures only staff can be assigned
        help_text="The admin/staff member handling this chat.",
    )

    # --- Unread Flags (for notifications) ---
    user_has_unread = models.BooleanField(
        default=False, help_text="True if the user has unread messages in this thread."
    )
    admin_has_unread = models.BooleanField(
        default=False, help_text="True if an admin has unread messages in this thread."
    )
    # ---------------------------------------

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        try:
            return f"Chat on {self.product.name} with {self.user.username}"
        except Exception:
            return f"Chat conversation {self.id}"


class ChatMessage(models.Model):
    """
    An individual message within a ChatConversation.
    """

    conversation = models.ForeignKey(
        ChatConversation, on_delete=models.CASCADE, related_name="messages"
    )
    sender = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="sent_messages"
    )
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        try:
            return f"Message from {self.sender.username}"
        except Exception:
            return f"Chat message {self.id}"
