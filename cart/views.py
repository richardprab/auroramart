from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from decimal import Decimal
from .models import Cart, CartItem
from products.models import Product, ProductVariant


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


def cart_detail(request):
    """Display cart contents"""
    cart = get_or_create_cart(request)
    cart_items = cart.items.select_related("product", "product_variant").all()

    # Remove invalid items (no variant)
    for it in list(cart_items):
        if not it.product_variant:
            it.delete()

    cart_items = cart.items.select_related("product", "product_variant").all()

    # Per-line totals
    for it in cart_items:
        price = it.product_variant.price or Decimal("0")
        it.line_total = (price * it.quantity).quantize(Decimal("0.01"))

    # Order summary
    subtotal = sum((it.line_total for it in cart_items), Decimal("0.00"))
    tax = (subtotal * Decimal("0.10")).quantize(Decimal("0.01"))
    shipping = Decimal("10.00") if cart_items else Decimal("0.00")
    total = (subtotal + tax + shipping).quantize(Decimal("0.01"))

    context = {
        "cart_items": cart_items,
        "subtotal": subtotal,
        "tax": tax,
        "shipping": shipping,
        "total": total,
    }
    return render(request, "cart/cart.html", context)


def add_to_cart(request, product_id):
    """Add product to cart"""
    if request.method == "POST":
        product = get_object_or_404(Product, id=product_id)
        variant_id = request.POST.get("variant_id")
        quantity = int(request.POST.get("quantity", 1))

        if not variant_id:
            messages.error(request, "Please select a product variant.")
            return redirect("products:product_detail", slug=product.slug)

        variant = get_object_or_404(ProductVariant, id=variant_id, product=product)

        # Check stock
        if variant.stock < quantity:
            messages.error(request, f"Only {variant.stock} items available in stock.")
            return redirect("products:product_detail", slug=product.slug)

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
                messages.error(
                    request, f"Cannot add more. Only {variant.stock} items available."
                )
                return redirect("cart:cart_detail")
            cart_item.quantity = new_quantity
            cart_item.save()

        messages.success(request, f"{product.name} added to cart!")
        return redirect("cart:cart_detail")

    return redirect("products:product_list")


def update_cart(request, item_id):
    """Update cart item quantity"""
    if request.method == "POST":
        cart = get_or_create_cart(request)
        try:
            item = cart.items.select_related("product_variant", "product").get(
                id=item_id
            )

            # Check if variant exists
            if not item.product_variant:
                item.delete()
                messages.error(request, "Invalid cart item removed.")
                return redirect("cart:cart_detail")

            quantity = int(request.POST.get("quantity", 1))

            if quantity < 1:
                item.delete()
                messages.success(request, f"{item.product.name} removed from cart.")
            else:
                # Check stock
                if quantity > item.product_variant.stock:
                    messages.error(
                        request, f"Only {item.product_variant.stock} items available."
                    )
                    quantity = item.product_variant.stock

                item.quantity = quantity
                item.save()
                messages.success(request, f"{item.product.name} quantity updated.")
        except CartItem.DoesNotExist:
            messages.error(request, "Item not found in cart.")
        except Exception as e:
            messages.error(request, f"Error updating cart: {str(e)}")

    return redirect("cart:cart_detail")


def remove_from_cart(request, item_id):
    """Remove item from cart"""
    if request.method == "POST":
        cart = get_or_create_cart(request)
        try:
            item = cart.items.get(id=item_id)
            product_name = item.product.name
            item.delete()
            messages.success(request, f"{product_name} removed from cart.")
        except CartItem.DoesNotExist:
            messages.error(request, "Item not found in cart.")

    return redirect("cart:cart_detail")


def clear_cart(request):
    """Clear all items from cart"""
    if request.method == "POST":
        cart = get_or_create_cart(request)
        count = cart.items.count()
        cart.items.all().delete()
        messages.success(request, f"Cart cleared! {count} item(s) removed.")

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
