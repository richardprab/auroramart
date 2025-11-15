from decimal import Decimal
from django.conf import settings


def calculate_dynamic_price(variant):
    # Check if dynamic pricing is enabled
    if not getattr(settings, 'DYNAMIC_PRICING_ENABLED', True):
        return variant.price
    
    # Check if variant is already on sale - do NOT apply dynamic pricing
    if variant.compare_price and variant.compare_price > variant.price:
        return variant.price
    
    # Get configuration
    threshold = getattr(settings, 'DYNAMIC_PRICING_LOW_STOCK_THRESHOLD', 10)
    discount_percentage = getattr(settings, 'DYNAMIC_PRICING_DISCOUNT_PERCENTAGE', 15)
    
    # Check if stock is low enough to trigger dynamic pricing
    if variant.stock > threshold:
        return variant.price
    
    # Apply discount
    base_price = Decimal(str(variant.price))
    discount_amount = (base_price * Decimal(str(discount_percentage)) / Decimal('100')).quantize(Decimal('0.01'))
    discounted_price = (base_price - discount_amount).quantize(Decimal('0.01'))
    
    # Ensure price doesn't go below zero
    return max(discounted_price, Decimal('0.01'))


def get_effective_price(variant):
    return calculate_dynamic_price(variant)


def get_effective_price_for_queryset(variants):
    result = {}
    for variant in variants:
        result[variant.id] = get_effective_price(variant)
    return result

