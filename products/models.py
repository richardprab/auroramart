from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.text import slugify


# Models related to the product catalog, including categories, products,
# variants, attributes, and images.


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
    size_guide = models.TextField(blank=True, null=True, help_text="NEW: From ERD")

    # --- Denormalized Review Data (from your snippet) ---
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.0)
    review_count = models.IntegerField(default=0)

    # --- Merchandising Flags (from your snippet) ---
    is_trending = models.BooleanField(default=False)
    is_bestseller = models.BooleanField(default=False)
    is_featured = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    # --- Timestamps ---
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # --- MOVED TO ProductVariant ---
    # price
    # compare_price
    # stock

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

    def get_default_variant(self):
        """Get the first active variant"""
        return self.variants.filter(is_active=True).first()

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
    display_order = models.IntegerField(
        default=0, name="order"
    )  # Keep your field name 'order'
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["order", "-is_primary"]

    def __str__(self):
        return f"{self.product.name} - Image {self.order}"


class Review(models.Model):
    """
    Product reviews (from your existing snippet).
    """

    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="reviews"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,  # Use settings.AUTH_USER_MODEL
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
        return f"{self.product.name} - {self.user.username} ({self.rating}★)"


class Attribute(models.Model):
    """
    NEW: Model for product attributes (e.g., 'Color', 'Size').
    """

    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class AttributeValue(models.Model):
    """
    NEW: Model for attribute values (e.g., 'Red', 'Large').
    """

    attribute = models.ForeignKey(
        Attribute, on_delete=models.CASCADE, related_name="values"
    )
    value = models.CharField(max_length=100)

    class Meta:
        unique_together = ("attribute", "value")

    def __str__(self):
        return f"{self.attribute.name}: {self.value}"


class ProductVariant(models.Model):
    """
    NEW: Model for product variants (e.g., 'Red, Large T-Shirt').
    This now holds Price, SKU, and Stock.
    """

    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="variants"
    )
    sku = models.CharField(max_length=100, unique=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    compare_price = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    sale_end_date = models.DateTimeField(null=True, blank=True)
    stock = models.IntegerField(default=0)
    main_image = models.ForeignKey(
        ProductImage,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="variant_main_image",
        help_text="Main image for this specific variant.",
    )
    attributes = models.ManyToManyField(
        AttributeValue, through="ProductVariantAttribute"
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.product.name} ({self.sku})"

    @property
    def is_on_sale(self):
        return self.compare_price and self.compare_price > self.price

    @property
    def discount_percentage(self):
        if self.is_on_sale:
            return int(((self.compare_price - self.price) / self.compare_price) * 100)
        return 0


class ProductVariantAttribute(models.Model):
    """
    NEW: Through table for Variant <-> AttributeValue.
    """

    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE)
    value = models.ForeignKey(AttributeValue, on_delete=models.CASCADE)

    class Meta:
        unique_together = ("variant", "value")


class RelatedProduct(models.Model):
    """
    NEW: Model for 'Frequently Bought Together' or 'Alternatives'.
    """

    RELATION_TYPE_CHOICES = [
        ("complementary", "Complementary (Frequently Bought Together)"),
        ("alternative", "Alternative (Others Also Viewed)"),
    ]
    from_product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="related_from"
    )
    to_product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="related_to"
    )
    relation_type = models.CharField(max_length=15, choices=RELATION_TYPE_CHOICES)

    class Meta:
        unique_together = ("from_product", "to_product", "relation_type")
