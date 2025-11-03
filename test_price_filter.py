"""
Test script to verify price filtering works
"""
from products.models import Product, ProductVariant
from django.db.models import Q
from decimal import Decimal

print("=" * 60)
print("PRICE FILTER TEST")
print("=" * 60)

# Get all products
all_products = Product.objects.filter(is_active=True)
print(f"\nTotal active products: {all_products.count()}")

# Show some variant prices
print("\nSample variant prices:")
for v in ProductVariant.objects.filter(is_active=True).order_by('price')[:10]:
    print(f"  ${v.price} - {v.product.name} ({v.sku})")

# Test filter with min=50, max=150
print("\n" + "-" * 60)
print("Testing filter: min_price=50, max_price=150")
print("-" * 60)

price_conditions = Q(variants__price__gte=Decimal('50')) & Q(variants__price__lte=Decimal('150'))
filtered_products = all_products.filter(price_conditions & Q(variants__is_active=True)).distinct()

print(f"\nFiltered products count: {filtered_products.count()}")
print("\nFiltered products:")
for p in filtered_products:
    variants = p.variants.filter(is_active=True)
    prices = [str(v.price) for v in variants]
    print(f"  - {p.name}: ${', $'.join(prices)}")

print("\n" + "=" * 60)
print("TEST COMPLETE")
print("=" * 60)
