from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.text import slugify


class Category(models.Model):
    """
    Product category (from your existing snippet).
    """

    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="children",
    )
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to="categories/", blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Categories"
        ordering = ["name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Product(models.Model):
    """
    Product model (from your snippet), MODIFIED to be a parent for variants.
    Price, SKU, and Stock have been MOVED to ProductVariant.
    """

    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    sku = models.CharField(
        max_length=100, unique=True, help_text="Base SKU for the product group."
    )
    category = models.ForeignKey(
        Category, on_delete=models.CASCADE, related_name="products"
    )
    description = models.TextField()
    brand = models.CharField(
        max_length=100, blank=True, help_text="Product brand/manufacturer"
    )
    
    # --- Product Data from CSV ---
    rating = models.DecimalField(
        max_digits=3, 
        decimal_places=2, 
        default=0.0,
        help_text="Product rating from CSV data"
    )
    reorder_quantity = models.PositiveIntegerField(
        default=0,
        help_text="Reorder quantity threshold (from CSV)"
    )

    # --- Product Status ---
    is_active = models.BooleanField(default=True)

    # --- Timestamps ---
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    @property
    def is_available(self):
        """Checks if the product has any active variants with stock."""
        return (
            self.is_active
            and self.variants.filter(is_active=True, stock__gt=0).exists()
        )

    def get_primary_image(self):
        """Get the primary product image"""
        return self.images.filter(is_primary=True).first() or self.images.first()
    
    def get_lowest_priced_variant(self):
        """Get the variant with the lowest price (already discounted)"""
        return self.variants.filter(is_active=True).order_by("price").first()

    def get_price_range(self):
        """Get min and max price from variants"""
        variants = self.variants.filter(is_active=True)
        if not variants.exists():
            return None, None
        prices = variants.values_list("price", flat=True)
        return min(prices), max(prices)

    def has_stock(self):
        """Check if any variant has stock"""
        return self.variants.filter(is_active=True, stock__gt=0).exists()


class ProductImage(models.Model):
    """
    Product images (from your existing snippet).
    """

    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="images"
    )
    image = models.ImageField(upload_to="products/")
    alt_text = models.CharField(max_length=200, blank=True)
    is_primary = models.BooleanField(default=False)
    display_order = models.IntegerField(default=0, db_column="order")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["display_order", "-is_primary"]

    def __str__(self):
        return f"{self.product.name} - Image {self.display_order}"


class Review(models.Model):
    """
    Product reviews (from your existing snippet).
    """

    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="reviews"
    )
    # Use settings.AUTH_USER_MODEL string reference instead of get_user_model()
    # Note: nullable initially to avoid circular migration dependency with accounts
    # This will be made required in a later migration
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
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


class ProductVariant(models.Model):
    """
    Model for product variants (e.g., 'Red, Large T-Shirt').
    This now holds Price, SKU, and Stock.
    """

    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="variants"
    )
    sku = models.CharField(max_length=100, unique=True)

    color = models.CharField(
        max_length=50, blank=True, help_text="Color option (e.g., Red, Blue)"
    )
    size = models.CharField(
        max_length=50, blank=True, help_text="Size option (e.g., S, M, L, XL)"
    )
    material = models.CharField(
        max_length=100, blank=True, help_text="Material (e.g., Cotton, Leather)"
    )

    price = models.DecimalField(max_digits=10, decimal_places=2)
    compare_price = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    stock = models.PositiveIntegerField(default=0)
    weight = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Weight in kg",
    )

    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-is_default", "price"]
        unique_together = [["product", "color", "size"]]

    def __str__(self):
        attrs = []
        if self.color:
            attrs.append(self.color)
        if self.size:
            attrs.append(self.size)
        variant_name = f" ({', '.join(attrs)})" if attrs else ""
        return f"{self.product.name}{variant_name} - {self.sku}"

    @property
    def is_on_sale(self):
        return self.compare_price and self.compare_price > self.price

    @property
    def discount_percentage(self):
        if self.is_on_sale:
            return int(((self.compare_price - self.price) / self.compare_price) * 100)
        return 0


