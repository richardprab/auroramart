# Testing Dynamic Pricing Implementation

## Quick Test Steps

### 1. Verify Settings
Check that dynamic pricing is enabled in `settings.py`:
- `DYNAMIC_PRICING_ENABLED = True`
- `DYNAMIC_PRICING_LOW_STOCK_THRESHOLD = 10`
- `DYNAMIC_PRICING_DISCOUNT_PERCENTAGE = 15`

### 2. Create Test Scenarios

#### Scenario A: Product with Low Stock (Should Get Discount)
1. Go to admin panel or use Django shell
2. Find or create a product variant with:
   - Stock ≤ 10 (e.g., stock = 5)
   - NOT on sale (no `compare_price` or `compare_price <= price`)
   - Base price = $100.00

3. Expected Result:
   - Displayed price should be $85.00 (15% discount)
   - Original price ($100.00) should be shown crossed out
   - "Low Stock" badge should appear

#### Scenario B: Product with High Stock (No Discount)
1. Same product but set stock = 20
2. Expected Result:
   - Displayed price should be $100.00 (no discount)
   - No "Low Stock" badge

#### Scenario C: Product Already on Sale (No Dynamic Pricing)
1. Product with:
   - Stock ≤ 10
   - `compare_price = $120.00` and `price = $90.00` (already on sale)
2. Expected Result:
   - Displayed price should be $90.00 (sale price, NOT discounted further)
   - Should show sale badge, NOT "Low Stock" badge

### 3. Where to Check

#### Frontend Pages:
- **Product List Page** (`/products/`):
  - Products with low stock should show discounted price
  - Look for "Low Stock" orange badge
  
- **Product Detail Page** (`/products/{sku}/`):
  - Price section should show effective price
  - If dynamically priced, shows "Low Stock Sale" badge
  
- **Cart Page** (`/cart/`):
  - Cart items should show effective prices
  - Subtotal should reflect discounted prices

- **Checkout Page** (`/orders/checkout/`):
  - Item prices should be effective prices
  - Totals should be calculated correctly

#### Backend/Database:
```python
# Django Shell Test
python manage.py shell

from products.models import ProductVariant
from products.pricing import get_effective_price

# Get a variant with low stock
variant = ProductVariant.objects.filter(stock__lte=10).first()

if variant:
    print(f"Base Price: ${variant.price}")
    print(f"Stock: {variant.stock}")
    print(f"Effective Price: ${variant.effective_price}")
    print(f"Is Dynamically Priced: {variant.is_dynamically_priced}")
    print(f"Original Price: ${variant.original_price}")
```

### 4. Test Cart Calculations

1. Add a product with low stock to cart
2. Check cart totals:
   - Subtotal should use effective price
   - Tax should be calculated on discounted subtotal
   - Shipping should be calculated correctly

### 5. Test Voucher Compatibility

1. Add low-stock items to cart (with dynamic pricing)
2. Apply a voucher code
3. Verify:
   - Voucher discount is calculated on effective prices
   - Total discount = voucher discount (not dynamic pricing + voucher)
   - Order is created with correct prices

### 6. Test Order Creation

1. Complete checkout with low-stock items
2. Check order in admin panel:
   - `OrderItem.price` should be the effective price at time of purchase
   - Order totals should match what was displayed

### 7. Visual Indicators

Look for these in the UI:
- ✅ **Orange "Low Stock" badge** - When dynamic pricing is active
- ✅ **Crossed-out original price** - Shows base price when discounted
- ✅ **Green "SALE" badge** - For items already on sale (different from dynamic pricing)

### 8. Edge Cases to Test

1. **Stock changes after adding to cart:**
   - Add item with stock = 11 (no discount)
   - Reduce stock to 5 (should now show discount)
   - Refresh cart page - price should update

2. **Multiple variants:**
   - Product with multiple variants
   - Some variants have low stock, others don't
   - Verify correct variant shows correct price

3. **Stock = 0:**
   - Product with 0 stock should not show dynamic pricing
   - Should show "Out of Stock" instead

## Quick Verification Script

Run this in Django shell to check all variants:

```python
from products.models import ProductVariant
from products.pricing import get_effective_price

variants = ProductVariant.objects.filter(is_active=True, stock__lte=10)[:5]

for v in variants:
    is_on_sale = v.compare_price and v.compare_price > v.price
    print(f"\n{v.product.name} - {v.sku}")
    print(f"  Stock: {v.stock}")
    print(f"  Base Price: ${v.price}")
    print(f"  Effective Price: ${v.effective_price}")
    print(f"  Is on Sale: {is_on_sale}")
    print(f"  Is Dynamically Priced: {v.is_dynamically_priced}")
    if v.is_dynamically_priced and not is_on_sale:
        discount = ((v.price - v.effective_price) / v.price * 100)
        print(f"  ✅ Dynamic Discount: {discount:.1f}%")
```

## Common Issues to Check

1. **Price not updating:**
   - Clear browser cache
   - Check that `DYNAMIC_PRICING_ENABLED = True`
   - Verify stock is actually ≤ threshold

2. **Discount not showing:**
   - Check if item is already on sale (dynamic pricing won't apply)
   - Verify stock level is correct
   - Check browser console for JavaScript errors

3. **Cart totals wrong:**
   - Verify `calculate_cart_totals()` uses `effective_price`
   - Check voucher calculations use effective prices

## Expected Behavior Summary

| Scenario | Stock | On Sale? | Expected Price | Badge |
|----------|-------|----------|---------------|-------|
| Low stock, not on sale | ≤10 | No | Base × 0.85 | "Low Stock" |
| High stock, not on sale | >10 | No | Base | None |
| Low stock, on sale | ≤10 | Yes | Sale price | "SALE" |
| High stock, on sale | >10 | Yes | Sale price | "SALE" |

