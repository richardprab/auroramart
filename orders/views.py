from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings
from django.db import transaction
from django.http import JsonResponse
from .models import Order, OrderItem
from cart.models import Cart
from cart.views import get_or_create_cart, calculate_cart_totals
from decimal import Decimal
import re
import logging

logger = logging.getLogger(__name__)


@login_required
def checkout(request):
    """Display checkout page"""
    cart = get_or_create_cart(request)
    cart_items = cart.items.select_related("product", "product_variant").all()

    if not cart_items:
        messages.info(request, "Your cart is empty. Add some items before checkout.")
        return redirect("cart:cart_detail")

    # Get voucher code from session or request
    voucher_code = request.session.get('applied_voucher_code', None)
    
    # Calculate totals using helper function (with voucher if applied)
    totals = calculate_cart_totals(cart_items, voucher_code=voucher_code, user=request.user)
    
    # Get user's saved addresses
    from accounts.models import Address
    all_saved_addresses = Address.objects.filter(user=request.user, address_type='shipping').order_by('-is_default', '-created_at')
    default_address = all_saved_addresses.filter(is_default=True).first()
    # If no default, use the first address
    if not default_address and all_saved_addresses.exists():
        default_address = all_saved_addresses.first()
    
    context = {
        "cart_items": cart_items,
        "subtotal": totals['subtotal'],
        "tax": totals['tax'],
        "shipping": totals['shipping'],
        "discount": totals.get('discount', 0),
        "total": totals['total'],
        "voucher_code": totals.get('voucher_code'),
        "user": request.user,
        "saved_addresses": all_saved_addresses,
        "default_address": default_address,
    }

    return render(request, "orders/checkout.html", context)


@login_required
def process_checkout(request):
    """Process the checkout and create order"""
    if request.method != 'POST':
        messages.warning(request, "Invalid request method.")
        return redirect('orders:checkout')
    
    # Debug: Log all POST data
    logger.info(f"=== CHECKOUT DEBUG ===")
    logger.info(f"User: {request.user.username}")
    logger.info(f"POST keys: {list(request.POST.keys())}")
    
    cart = get_or_create_cart(request)
    cart_items = cart.items.select_related("product", "product_variant").all()

    if not cart_items:
        messages.error(request, "Your cart is empty.")
        return redirect("cart:cart_detail")

    # Get form data
    shipping_address = request.POST.get('shipping_address', '').strip()
    billing_address = request.POST.get('billing_address', '').strip()
    payment_method = request.POST.get('payment_method', 'credit_card')
    
    # Debug logging
    logger.info(f"Shipping address length: {len(shipping_address)}")
    logger.info(f"Payment method: {payment_method}")
    
    # Validation
    if not shipping_address:
        logger.error("Shipping address is empty!")
        messages.error(request, "Please provide a shipping address.")
        return redirect('orders:checkout')
    
    # If billing address is not provided, use shipping address
    if not billing_address:
        billing_address = shipping_address
        logger.info("Using shipping address as billing address")

    try:
        with transaction.atomic():
            # Get voucher code from session
            voucher_code = request.session.get('applied_voucher_code', None)
            voucher = None
            discount_amount = Decimal('0.00')
            
            # Validate and apply voucher if present
            if voucher_code:
                try:
                    from vouchers.utils import apply_voucher_to_cart
                    
                    # Calculate subtotal for voucher validation
                    subtotal_before_voucher = sum(
                        ((item.product_variant.price or Decimal("0")) * item.quantity).quantize(Decimal("0.01"))
                        for item in cart_items
                    )
                    
                    # Calculate shipping for voucher validation
                    if subtotal_before_voucher < Decimal(str(settings.FREE_SHIPPING_THRESHOLD)):
                        shipping_before_voucher = Decimal(str(settings.SHIPPING_COST))
                    else:
                        shipping_before_voucher = Decimal("0.00")
                    
                    # Apply voucher
                    voucher_result = apply_voucher_to_cart(
                        voucher_code, request.user, cart_items, subtotal_before_voucher, shipping_before_voucher
                    )
                    voucher = voucher_result['voucher']
                    discount_amount = voucher_result['discount_amount']
                    logger.info(f"✅ Voucher {voucher_code} applied - Discount: ${discount_amount}")
                except Exception as e:
                    logger.warning(f"⚠️ Voucher validation failed: {str(e)}")
                    # Continue without voucher if validation fails
                    voucher_code = None
                    discount_amount = Decimal('0.00')
            
            # Calculate totals (with voucher if applied)
            totals = calculate_cart_totals(cart_items, voucher_code=voucher_code, user=request.user)
            
            # Extract phone number from shipping address
            phone_match = re.search(r'Phone:\s*(.+?)(?:\n|$)', shipping_address)
            contact_number = phone_match.group(1).strip() if phone_match else ''
            
            logger.info(f"Creating order - Subtotal: {totals['subtotal']}, Tax: {totals['tax']}, Shipping: {totals['shipping']}, Discount: {discount_amount}, Total: {totals['total']}")
            logger.info(f"Contact number: {contact_number}")
            
            # Create order - ONLY using fields that exist in Order model
            order = Order.objects.create(
                user=request.user,
                address=None,  # ForeignKey to Address model, set to None
                delivery_address=shipping_address,  # TextField for full delivery address
                contact_number=contact_number,  # Phone number extracted from address
                payment_method=payment_method,
                status='pending',
                subtotal=totals['subtotal'],
                tax=totals['tax'],
                shipping_cost=totals['shipping'],
                voucher_code=voucher_code or '',
                discount_amount=discount_amount,
                total=totals['total'],  # Use 'total' field only
                payment_status='pending'
            )
            
            logger.info(f"✅ Order created successfully: {order.order_number} (ID: {order.id})")
            
            # Track voucher usage if voucher was applied
            if voucher and discount_amount > 0:
                from vouchers.models import VoucherUsage
                VoucherUsage.objects.create(
                    voucher=voucher,
                    user=request.user,
                    order=order,
                    discount_amount=discount_amount
                )
                
                # Update voucher usage count
                voucher.current_uses += 1
                voucher.save()
                
                logger.info(f"✅ Voucher usage tracked for {voucher_code}")
            
            # Clear voucher from session after successful order
            if 'applied_voucher_code' in request.session:
                del request.session['applied_voucher_code']
                request.session.modified = True
            
            # Create order items
            for cart_item in cart_items:
                item_price = cart_item.product_variant.price if cart_item.product_variant else cart_item.product.price
                
                order_item = OrderItem.objects.create(
                    order=order,
                    product=cart_item.product,
                    product_variant=cart_item.product_variant,
                    quantity=cart_item.quantity,
                    price=item_price
                )
                
                logger.info(f"✅ Created order item: {cart_item.product.name} x {cart_item.quantity} @ ${item_price}")
                
                # Update product stock
                if cart_item.product_variant:
                    if cart_item.product_variant.stock >= cart_item.quantity:
                        cart_item.product_variant.stock -= cart_item.quantity
                        cart_item.product_variant.save()
                        # Use variant ID instead of name since it doesn't have a name attribute
                        logger.info(f"✅ Updated stock for variant ID {cart_item.product_variant.id} (remaining: {cart_item.product_variant.stock})")
                    else:
                        logger.error(f"❌ Insufficient stock for {cart_item.product.name} variant ID {cart_item.product_variant.id}")
                        raise ValueError(f"Insufficient stock for {cart_item.product.name}")
                else:
                    # If no variant, update main product stock
                    if cart_item.product.stock >= cart_item.quantity:
                        cart_item.product.stock -= cart_item.quantity
                        cart_item.product.save()
                        logger.info(f"✅ Updated stock for product: {cart_item.product.name} (remaining: {cart_item.product.stock})")
                    else:
                        logger.error(f"❌ Insufficient stock for {cart_item.product.name}")
                        raise ValueError(f"Insufficient stock for {cart_item.product.name}")
            
            # Clear cart
            deleted_count = cart_items.count()
            cart_items.delete()
            logger.info(f"✅ Cart cleared - {deleted_count} items removed")
            
            messages.success(request, f"Order {order.order_number} placed successfully! Thank you for your purchase.")
            logger.info(f"✅ Redirecting to order detail page for order {order.id}")
            return redirect('orders:order_detail', order_id=order.id)
            
    except ValueError as ve:
        logger.error(f"❌ Validation error: {str(ve)}")
        messages.error(request, str(ve))
        return redirect('orders:checkout')
    except Exception as e:
        logger.error(f"❌ Checkout error for user {request.user.username}: {str(e)}", exc_info=True)
        messages.error(request, f"An error occurred while processing your order. Please try again.")
        return redirect('orders:checkout')


@login_required
def order_list(request):
    """List user's orders grouped by status"""
    orders = Order.objects.filter(user=request.user).select_related('user').prefetch_related('items__product', 'items__product_variant').order_by("-created_at")
    
    # Status display names and colors
    status_info = {
        'pending': {'name': 'Pending', 'color': 'warning', 'icon': 'clock'},
        'processing': {'name': 'Processing', 'color': 'info', 'icon': 'cog'},
        'shipped': {'name': 'Shipped', 'color': 'primary', 'icon': 'truck'},
        'delivered': {'name': 'Delivered', 'color': 'success', 'icon': 'check-circle'},
        'cancelled': {'name': 'Cancelled', 'color': 'danger', 'icon': 'times-circle'},
    }
    
    # Group orders by status with their info
    orders_by_status = []
    for status, info in status_info.items():
        status_orders = orders.filter(status=status)
        orders_by_status.append({
            'status': status,
            'info': info,
            'orders': status_orders,
            'count': status_orders.count()
        })

    context = {
        "orders": orders,
        "orders_by_status": orders_by_status,
        "status_info": status_info,
    }
    return render(request, "orders/order_list.html", context)


@login_required
def order_detail(request, order_id):
    """Order detail page"""
    order = get_object_or_404(
        Order.objects.select_related('user').prefetch_related('items__product', 'items__product_variant', 'items__product__images'),
        id=order_id, 
        user=request.user
    )
    
    # Status information
    status_info = {
        'pending': {'name': 'Pending', 'color': 'warning', 'icon': 'clock', 'description': 'Your order has been received and is awaiting processing.'},
        'processing': {'name': 'Processing', 'color': 'info', 'icon': 'cog', 'description': 'Your order is currently being prepared.'},
        'shipped': {'name': 'Shipped', 'color': 'primary', 'icon': 'truck', 'description': 'Your order has been shipped and is on its way.'},
        'delivered': {'name': 'Delivered', 'color': 'success', 'icon': 'check-circle', 'description': 'Your order has been delivered successfully.'},
        'cancelled': {'name': 'Cancelled', 'color': 'danger', 'icon': 'times-circle', 'description': 'This order has been cancelled.'},
    }
    
    # Check review status for each product if order is delivered
    from reviews.models import Review
    items_with_reviews = []
    if order.status == 'delivered':
        for item in order.items.all():
            existing_review = None
            if request.user.is_authenticated:
                existing_review = Review.objects.filter(
                    user=request.user,
                    product=item.product
                ).first()
            
            items_with_reviews.append({
                'item': item,
                'has_review': existing_review is not None,
                'existing_review': existing_review,
            })
    else:
        # If not delivered, just add items without review info
        items_with_reviews = [{'item': item, 'has_review': False, 'existing_review': None} for item in order.items.all()]

    context = {
        "order": order,
        "current_status": status_info.get(order.status, {}),
        "status_info": status_info,
        "items_with_reviews": items_with_reviews,
    }
    return render(request, "orders/order_detail.html", context)


@login_required
def cancel_order(request, order_id):
    """Cancel an order - only pending orders can be cancelled"""
    if request.method != 'POST':
        messages.error(request, "Invalid request method.")
        return redirect('orders:order_detail', order_id=order_id)
    
    order = get_object_or_404(
        Order.objects.select_related('user'),
        id=order_id,
        user=request.user
    )
    
    # Only allow cancellation of pending orders
    if order.status != 'pending':
        messages.error(request, f"Cannot cancel order. Only pending orders can be cancelled. Current status: {order.status.title()}.")
        return redirect('orders:order_detail', order_id=order_id)
    
    try:
        with transaction.atomic():
            # Restore stock for all items
            for item in order.items.all():
                if item.product_variant:
                    item.product_variant.stock += item.quantity
                    item.product_variant.save()
                    logger.info(f"✅ Restored {item.quantity} units of stock for variant ID {item.product_variant.id}")
                else:
                    item.product.stock += item.quantity
                    item.product.save()
                    logger.info(f"✅ Restored {item.quantity} units of stock for product: {item.product.name}")
            
            # Update order status
            order.status = 'cancelled'
            order.save()
            
            logger.info(f"✅ Order {order.order_number} cancelled successfully by user {request.user.username}")
            messages.success(request, f"Order {order.order_number} has been cancelled successfully.")
            
    except Exception as e:
        logger.error(f"❌ Error cancelling order {order.order_number}: {str(e)}", exc_info=True)
        messages.error(request, "An error occurred while cancelling the order. Please try again.")
    
    return redirect('orders:order_detail', order_id=order_id)


@login_required
def apply_voucher(request):
    """AJAX endpoint to apply a voucher code to the cart"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid request method.'}, status=405)
    
    voucher_code = request.POST.get('voucher_code', '').strip()
    
    if not voucher_code:
        return JsonResponse({'success': False, 'error': 'Please enter a voucher code.'})
    
    cart = get_or_create_cart(request)
    cart_items = cart.items.select_related("product", "product_variant").all()
    
    if not cart_items:
        return JsonResponse({'success': False, 'error': 'Your cart is empty.'})
    
    try:
        from vouchers.utils import apply_voucher_to_cart
        
        # Calculate subtotal first
        from decimal import Decimal
        subtotal = sum(
            ((item.product_variant.price or Decimal("0")) * item.quantity).quantize(Decimal("0.01"))
            for item in cart_items
        )
        
        # Calculate shipping
        if subtotal < Decimal(str(settings.FREE_SHIPPING_THRESHOLD)):
            shipping = Decimal(str(settings.SHIPPING_COST))
        else:
            shipping = Decimal("0.00")
        
        # Apply voucher
        voucher_result = apply_voucher_to_cart(
            voucher_code, request.user, cart_items, subtotal, shipping
        )
        
        # Store voucher in session
        request.session['applied_voucher_code'] = voucher_code
        request.session.modified = True
        
        # Recalculate totals with voucher
        totals = calculate_cart_totals(cart_items, voucher_code=voucher_code, user=request.user)
        
        return JsonResponse({
            'success': True,
            'message': f'Voucher "{voucher_code}" applied successfully!',
            'discount': str(totals['discount']),
            'subtotal': str(totals['subtotal']),
            'tax': str(totals['tax']),
            'shipping': str(totals['shipping']),
            'total': str(totals['total']),
            'voucher_code': voucher_code,
            'voucher_description': voucher_result['voucher'].description or f"{voucher_result['voucher'].name} applied"
        })
        
    except Exception as e:
        # Remove voucher from session if validation failed
        if 'applied_voucher_code' in request.session:
            del request.session['applied_voucher_code']
            request.session.modified = True
        
        error_message = str(e)
        logger.error(f"Voucher application error: {error_message}")
        return JsonResponse({
            'success': False,
            'error': error_message
        })


@login_required
def remove_voucher(request):
    """AJAX endpoint to remove applied voucher"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid request method.'}, status=405)
    
    # Remove voucher from session
    if 'applied_voucher_code' in request.session:
        del request.session['applied_voucher_code']
        request.session.modified = True
    
    cart = get_or_create_cart(request)
    cart_items = cart.items.select_related("product", "product_variant").all()
    
    # Recalculate totals without voucher
    totals = calculate_cart_totals(cart_items, voucher_code=None, user=request.user)
    
    return JsonResponse({
        'success': True,
        'message': 'Voucher removed successfully.',
        'discount': '0.00',
        'subtotal': str(totals['subtotal']),
        'tax': str(totals['tax']),
        'shipping': str(totals['shipping']),
        'total': str(totals['total']),
    })