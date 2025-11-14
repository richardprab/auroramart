from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings
from django.db.models import Q
from django.utils import timezone

# Note: We use string references ("products.Category", "products.Product", "products.ProductVariant")
# to prevent circular import errors, which is a Django best practice.


class User(AbstractUser):
    """
    Base User model extending Django's AbstractUser.
    
    This model contains common fields for all user types (customers, staff, superusers).
    Customer-specific demographic fields are in the Customer model.
    
    Note: email, first_name, and last_name are inherited from AbstractUser.
    We override email to make it unique (AbstractUser doesn't enforce uniqueness).
    We override first_name and last_name to make them required (blank=False).
    """

    # --- Core Account Fields ---
    email = models.EmailField(
        unique=True, 
        help_text="Required. Used for login and communication.",
        blank=True, 
        null=True
    )
    # Override to make required (AbstractUser has these but allows blank)
    first_name = models.CharField(max_length=150, blank=True, default="")
    last_name = models.CharField(max_length=150, blank=True, default="")

    # Add timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Override groups and user_permissions to add related_name for multi-table inheritance
    groups = models.ManyToManyField(
        'auth.Group',
        verbose_name='groups',
        blank=True,
        help_text='The groups this user belongs to. A user will get all permissions granted to each of their groups.',
        related_name='%(class)s_set',
        related_query_name='user',
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        verbose_name='user permissions',
        blank=True,
        help_text='Specific permissions for this user.',
        related_name='%(class)s_set',
        related_query_name='user',
    )

    class Meta:
        abstract = True
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


class Superuser(User):
    """
    Superuser model extending User with multi-table inheritance.
    
    Superusers are User instances with is_superuser=True that are not
    Customer or Staff instances. This provides a convenient way
    to query and manage superusers separately.
    """
    
    class Meta:
        db_table = "superusers"
        verbose_name = "Superuser"
        verbose_name_plural = "Superusers"
    
    def save(self, *args, **kwargs):
        """Ensure superuser flag is set"""
        self.is_superuser = True
        self.is_staff = True  # Superusers are also staff
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"Superuser: {self.username}"


class Customer(User):
    """
    Customer model extending User with customer-specific demographic fields.
    
    Only customers (not staff/superusers) should have a Customer profile.
    This allows staff/superusers to exist without unnecessary demographic fields.
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
        ('Bachelor', "Bachelor's Degree"),
        ('Master', "Master's Degree"),
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
    phone = models.CharField(max_length=20, blank=True, null=True, help_text="Phone number. Optional.")
    avatar = models.ImageField(upload_to="avatars/", null=True, blank=True)

    class Meta:
        db_table = "customers"
        verbose_name = "Customer"
        verbose_name_plural = "Customers"

    def __str__(self):
        return f"Customer: {self.username}"
    
    def get_profile_completion_percentage(self):
        """Calculate how complete the customer's profile is for better recommendations."""
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


class Staff(User):
    """
    Staff model extending User with staff-specific permissions.
    
    Staff members have access to the admin panel with configurable permissions.
    Superusers use the Superuser proxy model (not Staff).
    """
    
    PERMISSION_CHOICES = [
        ('all', 'All Permissions'),
        ('products', 'Product Management'),
        ('orders', 'Order Management'),
        ('chat', 'Customer Support/Chat'),
        ('analytics', 'Analytics'),
        ('products,orders', 'Products & Orders'),
        ('products,chat', 'Products & Chat'),
        ('orders,chat', 'Orders & Chat'),
        ('products,orders,chat', 'Products, Orders & Chat'),
    ]
    
    permissions = models.CharField(
        max_length=255,
        default='all',
        choices=PERMISSION_CHOICES,
        help_text="Staff permissions for admin panel access. 'all' grants full access."
    )
    
    class Meta:
        db_table = "staff"
        verbose_name = "Staff"
        verbose_name_plural = "Staff"

    def __str__(self):
        return f"Staff: {self.username}"
    
    def has_permission(self, permission):
        """
        Check if staff member has a specific permission.
        
        Args:
            permission: One of 'products', 'orders', 'chat', 'analytics', or 'all'
        
        Returns:
            bool: True if staff has the permission
        """
        if self.permissions == 'all':
            return True
        return permission in self.permissions.split(',')
    
    def get_permissions_list(self):
        """
        Get list of permissions for this staff member.
        
        Returns:
            list: List of permission strings
        """
        if self.permissions == 'all':
            return ['all', 'products', 'orders', 'chat', 'analytics']
        return [p.strip() for p in self.permissions.split(',')]


class Address(models.Model):
    """
    Stores a shipping or billing address for a user.
    A user can have multiple addresses.
    """

    user = models.ForeignKey(
        'Customer',  # Addresses are customer-specific
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

    user = models.ForeignKey('Customer', on_delete=models.CASCADE, related_name='wishlist_items')
    product_variant = models.ForeignKey('products.ProductVariant', on_delete=models.CASCADE,  null=True, blank=True)
    product = models.ForeignKey('products.Product', on_delete=models.CASCADE, null=True, blank=True)
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

    user = models.ForeignKey('Customer', on_delete=models.CASCADE, related_name='sale_subscriptions')
    product_variant = models.ForeignKey('products.ProductVariant', on_delete=models.CASCADE)
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
    Tracks products a user has viewed with view count.
    One entry per user-product pair, updates timestamp on each view.
    Used for "Recently Viewed" feature and analytics.
    """

    user = models.ForeignKey('Customer', on_delete=models.CASCADE, related_name='browsing_history')
    product = models.ForeignKey('products.Product', on_delete=models.CASCADE, related_name='browsing_history')
    viewed_at = models.DateTimeField(auto_now=True)
    view_count = models.IntegerField(default=1)
    
    class Meta:
        verbose_name_plural = 'Browsing Histories'
        ordering = ['-viewed_at']
        unique_together = ('user', 'product')

    def __str__(self):
        return f"{self.user.username} viewed {self.product.name}"
