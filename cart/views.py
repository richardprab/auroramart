from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.conf import settings
from decimal import Decimal
from .models import Cart, CartItem
from products.models import Product, ProductVariant


def calculate_cart_totals(cart_items, voucher_code=None, user=None):
    """
    Calculate cart totals including subtotal, tax, shipping, and total.
    Optionally applies voucher discount.
    
    Args:
        cart_items: QuerySet of CartItem objects
        voucher_code: Optional voucher code to apply
        user: Optional user for voucher validation
        
    Returns:
        dict: Dictionary containing subtotal, tax, shipping, discount, total, and item_count
    """
    subtotal = sum(
        ((item.product_variant.price or Decimal("0")) * item.quantity).quantize(Decimal("0.01"))
        for item in cart_items
    )
    
    # Calculate shipping before voucher (needed for free shipping vouchers)
    if cart_items and subtotal < Decimal(str(settings.FREE_SHIPPING_THRESHOLD)):
        shipping = Decimal(str(settings.SHIPPING_COST))
    else:
        shipping = Decimal("0.00")
    
    # Apply voucher if provided
    discount_amount = Decimal("0.00")
    voucher = None
    if voucher_code and user:
        try:
            from vouchers.utils import apply_voucher_to_cart
            voucher_result = apply_voucher_to_cart(
                voucher_code, user, cart_items, subtotal, shipping
            )
            voucher = voucher_result['voucher']
            discount_amount = voucher_result['discount_amount']
            
            # Adjust subtotal or shipping based on voucher type
            if voucher.discount_type == 'free_shipping':
                shipping = voucher_result['new_shipping']
            else:
                subtotal = voucher_result['new_subtotal']
        except Exception as e:
            # Voucher validation failed, continue without discount
            pass
    
    # Calculate tax on subtotal (after discount if applicable)
    tax_rate = Decimal(str(settings.TAX_RATE))
    tax = (subtotal * tax_rate).quantize(Decimal("0.01"))
    
    # Calculate total
    total = (subtotal + tax + shipping).quantize(Decimal("0.01"))
    item_count = sum(item.quantity for item in cart_items)
    
    return {
        'subtotal': subtotal,
        'tax': tax,
        'shipping': shipping,
        'discount': discount_amount,
        'total': total,
        'item_count': item_count,
        'voucher': voucher,
        'voucher_code': voucher_code if voucher else None
    }


def get_or_create_cart(request):
    """Get or create cart for the current user/session"""
    if request.user.is_authenticated:
        cart, created = Cart.objects.get_or_create(user=request.user)
    else:
        session_key = request.session.session_key
        if not session_key:
            request.session.create()
            session_key = request.session.session_key
        cart, created = Cart.objects.get_or_create(session_key=session_key)
    return cart


def merge_session_cart_to_user(user, session_key):
    """
    Merge session cart into user's cart when user logs in.
    
    Args:
        user: The authenticated user
        session_key: The session key of the anonymous cart
    
    Returns:
        dict: Summary of merge operation with counts
    """
    if not session_key:
        return {'merged': 0, 'skipped': 0, 'message': 'No session cart to merge'}
    
    try:
        # Get session cart
        session_cart = Cart.objects.get(session_key=session_key, user__isnull=True)
    except Cart.DoesNotExist:
        return {'merged': 0, 'skipped': 0, 'message': 'No session cart found'}
    
    # Get or create user cart
    user_cart, _ = Cart.objects.get_or_create(user=user)
    
    merged_count = 0
    skipped_count = 0
    
    # Merge items from session cart to user cart
    for session_item in session_cart.items.all():
        if not session_item.product_variant:
            skipped_count += 1
            continue
        
        # Check if item already exists in user cart
        try:
            user_item = CartItem.objects.get(
                cart=user_cart,
                product_variant=session_item.product_variant
            )
            # Merge quantities (cap at available stock)
            new_quantity = user_item.quantity + session_item.quantity
            max_stock = session_item.product_variant.stock
            
            if new_quantity > max_stock:
                user_item.quantity = max_stock
                skipped_count += 1  # Partial merge
            else:
                user_item.quantity = new_quantity
            
            user_item.save()
            merged_count += 1
            
        except CartItem.DoesNotExist:
            # Item doesn't exist in user cart, transfer it
            max_stock = session_item.product_variant.stock
            
            if session_item.quantity > max_stock:
                session_item.quantity = max_stock
                skipped_count += 1  # Partial merge
            
            # Create new item in user cart
            CartItem.objects.create(
                cart=user_cart,
                product=session_item.product,
                product_variant=session_item.product_variant,
                quantity=session_item.quantity
            )
            merged_count += 1
    
    # Delete the session cart after merge
    session_cart.delete()
    
    return {
        'merged': merged_count,
        'skipped': skipped_count,
        'message': f'Merged {merged_count} items from session cart'
    }


def cart_detail(request):
    """Display cart contents"""
    cart = get_or_create_cart(request)
    cart_items = cart.items.select_related("product", "product_variant").all()

    # DEBUG: Print cart items for recommendation debugging
    print(f"DEBUG: Cart has {cart_items.count()} items")
    for item in cart_items:
        if item.product_variant:
            print(f"DEBUG: Cart item - Product: {item.product.name}, SKU: {item.product.sku}")
            print(f"DEBUG: Variant SKU: {item.product_variant.sku}")

    # Remove invalid items (no variant)
    for it in list(cart_items):
        if not it.product_variant:
            it.delete()

    cart_items = cart.items.select_related("product", "product_variant").all()

    # Per-line totals
    for it in cart_items:
        price = it.product_variant.price or Decimal("0")
        it.line_total = (price * it.quantity).quantize(Decimal("0.01"))

    # Calculate totals using helper function
    totals = calculate_cart_totals(cart_items)

    context = {
        "cart_items": cart_items,
        "subtotal": totals['subtotal'],
        "tax": totals['tax'],
        "shipping": totals['shipping'],
        "total": totals['total'],
    }
    return render(request, "cart/cart.html", context)


def add_to_cart(request, product_id):
    """Add product to cart"""
    if request.method == "POST":
        product = get_object_or_404(Product, id=product_id)
        variant_id = request.POST.get("variant_id")
        quantity = int(request.POST.get("quantity", 1))

        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

        if not variant_id:
            if is_ajax:
                return JsonResponse({
                    "success": False,
                    "message": "Please select size and color"
                })
            # No toast, just redirect back
            return redirect("products:product_detail", sku=product.sku)

        variant = get_object_or_404(ProductVariant, id=variant_id, product=product)

        # Check stock
        if variant.stock < quantity:
            if is_ajax:
                return JsonResponse({
                    "success": False,
                    "message": f"Only {variant.stock} left in stock"
                })
            # No toast, redirect back
            return redirect("products:product_detail", sku=product.sku)

        cart = get_or_create_cart(request)

        # Check if item already exists in cart
        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            product_variant=variant,
            defaults={"quantity": quantity},
        )

        if not created:
            # Update quantity if item exists
            new_quantity = cart_item.quantity + quantity
            if new_quantity > variant.stock:
                if is_ajax:
                    return JsonResponse({
                        "success": False,
                        "message": f"Only {variant.stock} available"
                    })
                # No toast
                return redirect("cart:cart_detail")
            cart_item.quantity = new_quantity
            cart_item.save()

        # Return JSON for AJAX requests (stay on same page)
        if is_ajax:
            cart_count = cart.items.count()
            return JsonResponse({
                "success": True,
                "message": "Added to cart",
                "cart_count": cart_count
            })

        # Regular form submission (redirect to cart) - no toast
        return redirect("cart:cart_detail")

    return redirect("products:product_list")


def update_cart(request, item_id):
    """Update cart item quantity"""
    if request.method == "POST":
        cart = get_or_create_cart(request)
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        
        try:
            item = cart.items.select_related("product_variant", "product").get(
                id=item_id
            )

            # Check if variant exists
            if not item.product_variant:
                item.delete()
                if is_ajax:
                    return JsonResponse({
                        "success": False,
                        "error": "Item removed - no longer available"
                    })
                # No toast
                return redirect("cart:cart_detail")

            quantity = int(request.POST.get("quantity", 1))

            if quantity < 1:
                product_name = item.product.name
                item.delete()
                
                if is_ajax:
                    # Recalculate totals after deletion
                    cart_items = cart.items.select_related("product", "product_variant").all()
                    totals = calculate_cart_totals(cart_items)
                    
                    return JsonResponse({
                        "success": True,
                        "message": f"{product_name} removed from cart.",
                        "removed": True,
                        "subtotal": str(totals['subtotal']),
                        "tax": str(totals['tax']),
                        "shipping": str(totals['shipping']),
                        "total": str(totals['total']),
                        "item_count": totals['item_count']
                    })
                
                # No toast for removed item
            else:
                # Check stock
                if quantity > item.product_variant.stock:
                    if is_ajax:
                        return JsonResponse({
                            "success": False,
                            "error": f"Only {item.product_variant.stock} available"
                        })
                    # No toast
                    quantity = item.product_variant.stock

                item.quantity = quantity
                item.save()
                
                if is_ajax:
                    # Calculate line total
                    price = item.product_variant.price or Decimal("0")
                    line_total = (price * item.quantity).quantize(Decimal("0.01"))
                    
                    # Recalculate order totals using helper function
                    cart_items = cart.items.select_related("product", "product_variant").all()
                    totals = calculate_cart_totals(cart_items)
                    
                    return JsonResponse({
                        "success": True,
                        "message": f"{item.product.name} quantity updated.",
                        "line_total": str(line_total),
                        "subtotal": str(totals['subtotal']),
                        "tax": str(totals['tax']),
                        "shipping": str(totals['shipping']),
                        "total": str(totals['total']),
                        "item_count": totals['item_count']
                    })
                
                # No toast for quantity update
                
        except CartItem.DoesNotExist:
            if is_ajax:
                return JsonResponse({
                    "success": False,
                    "error": "Item not found"
                })
            # No toast
        except Exception as e:
            if is_ajax:
                return JsonResponse({
                    "success": False,
                    "error": "Unable to update cart"
                })
            # No toast

    return redirect("cart:cart_detail")


def remove_from_cart(request, item_id):
    """Remove item from cart"""
    if request.method == "POST":
        cart = get_or_create_cart(request)
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        
        try:
            item = cart.items.get(id=item_id)
            product_name = item.product.name
            item.delete()
            
            if is_ajax:
                # Recalculate totals after deletion using helper function
                cart_items = cart.items.select_related("product", "product_variant").all()
                totals = calculate_cart_totals(cart_items)
                
                return JsonResponse({
                    "success": True,
                    "message": f"{product_name} removed from cart.",
                    "subtotal": str(totals['subtotal']),
                    "tax": str(totals['tax']),
                    "shipping": str(totals['shipping']),
                    "total": str(totals['total']),
                    "item_count": totals['item_count']
                })
            
            # No toast for removed item
        except CartItem.DoesNotExist:
            if is_ajax:
                return JsonResponse({
                    "success": False,
                    "error": "Item not found"
                })
            # No toast

    return redirect("cart:cart_detail")


def clear_cart(request):
    """Clear all items from cart"""
    if request.method == "POST":
        cart = get_or_create_cart(request)
        count = cart.items.count()
        cart.items.all().delete()
        # No toast for clear cart

    return redirect("cart:cart_detail")


def cart_count(request):
    """API endpoint to get cart item count"""
    try:
        cart = get_or_create_cart(request)
        # Only count items with valid variants
        count = sum(
            item.quantity
            for item in cart.items.all()
            if item.product_variant is not None
        )
        return JsonResponse({"count": count})
    except Exception as e:
        return JsonResponse({"count": 0, "error": str(e)})
