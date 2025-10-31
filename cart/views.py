from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from products.models import Product
from .models import Cart, CartItem


def get_or_create_cart(request):
    """Get or create cart for user or session"""
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
    cart_items = cart.items.all()

    context = {
        "cart": cart,
        "cart_items": cart_items,
    }
    return render(request, "cart/cart.html", context)


def add_to_cart(request, product_id):
    """Add product to cart"""
    if request.method == "POST":
        product = get_object_or_404(Product, id=product_id)
        cart = get_or_create_cart(request)
        quantity = int(request.POST.get("quantity", 1))

        # Get or create cart item
        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            defaults={"quantity": quantity},
        )

        if not created:
            cart_item.quantity += quantity
            cart_item.save()

        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse(
                {
                    "success": True,
                    "message": "Product added to cart",
                    "cart_count": cart.items.count(),
                }
            )

        messages.success(request, f"{product.name} added to cart!")
        return redirect("cart:cart_detail")

    return redirect("products:product_list")


def remove_from_cart(request, item_id):
    """Remove item from cart"""
    if request.method == "POST":
        cart = get_or_create_cart(request)
        cart_item = get_object_or_404(CartItem, id=item_id, cart=cart)
        product_name = cart_item.product.name
        cart_item.delete()

        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({"success": True, "message": "Item removed from cart"})

        messages.success(request, f"{product_name} removed from cart")
        return redirect("cart:cart_detail")

    return redirect("cart:cart_detail")


def update_cart(request, item_id):
    """Update cart item quantity"""
    if request.method == "POST":
        cart = get_or_create_cart(request)
        cart_item = get_object_or_404(CartItem, id=item_id, cart=cart)
        quantity = int(request.POST.get("quantity", 1))

        if quantity > 0:
            cart_item.quantity = quantity
            cart_item.save()
            message = "Cart updated"
        else:
            cart_item.delete()
            message = "Item removed from cart"

        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({"success": True, "message": message})

        messages.success(request, message)
        return redirect("cart:cart_detail")

    return redirect("cart:cart_detail")


def clear_cart(request):
    """Clear all items from cart"""
    if request.method == "POST":
        cart = get_or_create_cart(request)
        cart.items.all().delete()

        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({"success": True, "message": "Cart cleared"})

        messages.success(request, "Cart cleared")
        return redirect("cart:cart_detail")

    return redirect("cart:cart_detail")
