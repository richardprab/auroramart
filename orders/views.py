from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Order, OrderItem
from cart.models import Cart


@login_required
def checkout(request):
    """Checkout page"""
    cart = Cart.objects.filter(user=request.user).first()

    if not cart or not cart.items.exists():
        messages.warning(request, "Your cart is empty")
        return redirect("products:product_list")

    if request.method == "POST":
        # Create order
        order = Order.objects.create(
            user=request.user,
            first_name=request.POST.get("first_name"),
            last_name=request.POST.get("last_name"),
            email=request.POST.get("email"),
            phone=request.POST.get("phone"),
            address=request.POST.get("address"),
            city=request.POST.get("city"),
            state=request.POST.get("state"),
            zip_code=request.POST.get("zip_code"),
        )

        # Create order items from cart
        for cart_item in cart.items.all():
            OrderItem.objects.create(
                order=order,
                product=cart_item.product,
                quantity=cart_item.quantity,
                price=cart_item.product.price,
            )

        # Clear cart
        cart.items.all().delete()

        messages.success(request, f"Order #{order.id} placed successfully!")
        return redirect("orders:order_detail", order_id=order.id)

    context = {
        "cart": cart,
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
