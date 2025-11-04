from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings
from .models import Order, OrderItem
from cart.models import Cart
from cart.views import get_or_create_cart, calculate_cart_totals
from decimal import Decimal


@login_required
def checkout(request):
    """Display checkout page"""
    cart = get_or_create_cart(request)
    cart_items = cart.items.select_related("product", "product_variant").all()

    if not cart_items:
        messages.warning(request, "Your cart is empty.")
        return redirect("cart:cart_detail")

    # Calculate totals using helper function
    totals = calculate_cart_totals(cart_items)

    context = {
        "cart_items": cart_items,
        "subtotal": totals['subtotal'],
        "tax": totals['tax'],
        "shipping": totals['shipping'],
        "total": totals['total'],
    }

    return render(request, "orders/checkout.html", context)


@login_required
def order_list(request):
    """List user's orders"""
    orders = Order.objects.filter(user=request.user).order_by("-created_at")

    context = {
        "orders": orders,
    }
    return render(request, "orders/order_list.html", context)


@login_required
def order_detail(request, order_id):
    """Order detail page"""
    order = get_object_or_404(Order, id=order_id, user=request.user)

    context = {
        "order": order,
    }
    return render(request, "orders/order_detail.html", context)
