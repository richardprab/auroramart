"""
Voucher validation and calculation utilities.
Industry-standard voucher system with comprehensive validation.
"""
from decimal import Decimal
from .models import Voucher, VoucherUsage


class VoucherValidationError(Exception):
    """Custom exception for voucher validation errors."""
    pass


def validate_voucher(code, user, cart_items, subtotal):
    """
    Validate a voucher code and return the voucher if valid.
    
    Args:
        code: Voucher code string
        user: User attempting to use the voucher
        cart_items: QuerySet of cart items
        subtotal: Cart subtotal before discount
        
    Returns:
        Voucher: Valid voucher object
        
    Raises:
        VoucherValidationError: If voucher is invalid or cannot be used
    """
    if not code:
        raise VoucherValidationError("Voucher code is required.")
    
    code = code.upper().strip()
    
    try:
        voucher = Voucher.objects.get(promo_code=code)
    except Voucher.DoesNotExist:
        raise VoucherValidationError("Invalid voucher code.")
    
    # Check if voucher is valid (active and within date range)
    if not voucher.is_valid():
        raise VoucherValidationError("This voucher is not currently valid.")
    
    # Check if usage limit reached
    if voucher.is_usage_limit_reached():
        raise VoucherValidationError("This voucher has reached its usage limit.")
    
    # Check if user can use this voucher
    if not voucher.can_be_used_by_user(user):
        if voucher.user and voucher.user != user:
            raise VoucherValidationError("This voucher is not available for your account.")
        if voucher.first_time_only:
            raise VoucherValidationError("This voucher is only available for first-time customers.")
        raise VoucherValidationError("You have reached the maximum usage limit for this voucher.")
    
    # Check minimum purchase requirement
    if subtotal < voucher.min_purchase:
        raise VoucherValidationError(
            f"Minimum purchase of ${voucher.min_purchase} required. "
            f"Your cart total is ${subtotal}."
        )
    
    # Check product/category restrictions
    if voucher.applicable_products.exists() or voucher.applicable_categories.exists():
        valid_items = []
        # Cache querysets to avoid multiple queries
        applicable_product_ids = set(voucher.applicable_products.values_list('pk', flat=True)) if voucher.applicable_products.exists() else set()
        applicable_category_ids = set(voucher.applicable_categories.values_list('pk', flat=True)) if voucher.applicable_categories.exists() else set()
        
        for item in cart_items:
            product = item.product
            
            # Check if product is in applicable products list
            if applicable_product_ids and product.pk in applicable_product_ids:
                valid_items.append(item)
                continue
            
            # Check if product category is in applicable categories
            if applicable_category_ids and product.category and product.category.pk in applicable_category_ids:
                valid_items.append(item)
                continue
        
        if not valid_items:
            raise VoucherValidationError(
                "This voucher is not applicable to any items in your cart."
            )
        
        # Check exclude sale items
        if voucher.exclude_sale_items:
            for item in valid_items:
                variant = item.product_variant
                if variant and variant.is_on_sale:
                    raise VoucherValidationError(
                        "This voucher cannot be used on items that are already on sale."
                    )
    
    return voucher


def calculate_voucher_discount(voucher, subtotal, shipping_cost=Decimal('0')):
    """
    Calculate the discount amount for a voucher.
    
    Args:
        voucher: Voucher object
        subtotal: Cart subtotal before discount
        shipping_cost: Shipping cost (for free shipping vouchers)
        
    Returns:
        Decimal: Discount amount
    """
    discount = Decimal('0')
    
    if voucher.discount_type == 'fixed':
        # Fixed amount discount
        discount = min(voucher.discount_value, subtotal)
    
    elif voucher.discount_type == 'percent':
        # Percentage discount
        discount = (subtotal * voucher.discount_value / Decimal('100')).quantize(Decimal('0.01'))
        
        # Apply max discount cap if set
        if voucher.max_discount:
            discount = min(discount, voucher.max_discount)
        
        # Ensure discount doesn't exceed subtotal
        discount = min(discount, subtotal)
    
    elif voucher.discount_type == 'free_shipping':
        # Free shipping voucher
        discount = shipping_cost
    
    return discount.quantize(Decimal('0.01'))


def apply_voucher_to_cart(voucher_code, user, cart_items, subtotal, shipping_cost=Decimal('0')):
    """
    Apply a voucher to a cart and return discount details.
    
    Args:
        voucher_code: Voucher code string
        user: User applying the voucher
        cart_items: QuerySet of cart items
        subtotal: Cart subtotal before discount
        shipping_cost: Shipping cost
        
    Returns:
        dict: {
            'voucher': Voucher object,
            'discount_amount': Decimal,
            'new_subtotal': Decimal,
            'new_total': Decimal
        }
        
    Raises:
        VoucherValidationError: If voucher is invalid
    """
    # Validate voucher
    voucher = validate_voucher(voucher_code, user, cart_items, subtotal)
    
    # Calculate discount
    discount_amount = calculate_voucher_discount(voucher, subtotal, shipping_cost)
    
    # Calculate new totals
    new_subtotal = subtotal - discount_amount if voucher.discount_type != 'free_shipping' else subtotal
    new_shipping = shipping_cost - discount_amount if voucher.discount_type == 'free_shipping' else shipping_cost
    
    return {
        'voucher': voucher,
        'discount_amount': discount_amount,
        'new_subtotal': max(new_subtotal, Decimal('0')),
        'new_shipping': max(new_shipping, Decimal('0')),
    }

