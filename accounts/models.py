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

    GENDER_CHOICES = [
        ('Male', 'Male'),
        ('Female', 'Female'),
    ]
    
    EMPLOYMENT_STATUS_CHOICES = [
        ('Full-time', 'Full-time'),
        ('Part-time', 'Part-time'),
        ('Student', 'Student'),
        ('Self-employed', 'Self-employed'),
        ('Retired', 'Retired'),
    ]
    
    OCCUPATION_CHOICES = [
        ('Tech', 'Technology/IT'),
        ('Sales', 'Sales & Marketing'),
        ('Service', 'Service Industry'),
        ('Admin', 'Administrative'),
        ('Education', 'Education'),
        ('Skilled Trades', 'Skilled Trades'),
        ('Healthcare', 'Healthcare'),
        ('Finance', 'Finance & Banking'),
        ('Other', 'Other'),
    ]
    
    EDUCATION_CHOICES = [
        ('Secondary', 'Secondary/High School'),
        ('Diploma', 'Diploma/Certificate'),
        ('Bachelor', 'Bachelor\'s Degree'),
        ('Master', 'Master\'s Degree'),
        ('Doctorate', 'Doctorate/PhD'),
    ]
    
    age = models.IntegerField(
        null=True, 
        blank=True, 
        help_text="Age in years."
    )
    gender = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        choices=GENDER_CHOICES,
        help_text="Gender."
    )
    employment_status = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        choices=EMPLOYMENT_STATUS_CHOICES,
        help_text="Employment status."
    )
    occupation = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        choices=OCCUPATION_CHOICES,
        help_text="Occupation type. Optional."
    )
    education = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        choices=EDUCATION_CHOICES,
        help_text="Highest education level."
    )
    household_size = models.IntegerField(
        null=True, 
        blank=True, 
        help_text="Number of people in household. Optional."
    )
    has_children = models.BooleanField(
        null=True, 
        blank=True, 
        help_text="Has children. Optional."
    )
    monthly_income_sgd = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Monthly income in SGD. Optional, kept private."
    )

    # --- Core Account Fields ---
    email = models.EmailField(
        unique=True, help_text="Required. Used for login and communication."
    )
    first_name = models.CharField(max_length=150, blank=False)
    last_name = models.CharField(max_length=150, blank=False)

    # --- Optional Profile Fields ---
    phone = models.CharField(max_length=20, blank=True, null=True)
    avatar = models.ImageField(upload_to="avatars/", null=True, blank=True)

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
    
    def get_profile_completion_percentage(self):
        """Calculate how complete the user's profile is for better recommendations."""
        total_fields = 8  # age, gender, employment_status, occupation, education, household_size, has_children, monthly_income_sgd
        completed_fields = sum([
            self.age is not None,
            bool(self.gender),
            bool(self.employment_status),
            bool(self.occupation),
            bool(self.education),
            self.household_size is not None,
            self.has_children is not None,
            self.monthly_income_sgd is not None,
        ])
        return int((completed_fields / total_fields) * 100)
    
    def has_complete_profile_for_ml(self):
        """Check if user has enough data for ML recommendations."""
        # At minimum, we need age and gender for reasonable predictions
        return bool(self.age) and bool(self.gender)


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
