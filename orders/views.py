from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings
from django.db import transaction
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.urls import reverse
from .models import Order, OrderItem
from cart.models import Cart
from cart.views import get_or_create_cart, calculate_cart_totals
from decimal import Decimal
import re
import logging
import stripe
import json

logger = logging.getLogger(__name__)

# Initialize Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY


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
    """Process the checkout - create order and redirect to Stripe payment"""
    if request.method != 'POST':
        messages.warning(request, "Invalid request method.")
        return redirect('orders:checkout')
    
    cart = get_or_create_cart(request)
    cart_items = cart.items.select_related("product", "product_variant").all()

    if not cart_items:
        messages.error(request, "Your cart is empty.")
        return redirect("cart:cart_detail")

    # Get form data
    shipping_address = request.POST.get('shipping_address', '').strip()
    payment_method = request.POST.get('payment_method', 'credit_card')
    address_id = request.POST.get('address_id', '').strip()
    
    # Validation
    if not shipping_address:
        messages.error(request, "Please provide a shipping address.")
        return redirect('orders:checkout')

    try:
        with transaction.atomic():
            from accounts.models import Address
            
            # Handle address - either use existing or create new
            order_address = None
            if address_id:
                # Use existing saved address
                try:
                    order_address = Address.objects.get(id=address_id, user=request.user, address_type='shipping')
                except Address.DoesNotExist:
                    logger.warning(f"Address {address_id} not found for user {request.user.id}")
                    messages.error(request, "Selected address not found.")
                    return redirect('orders:checkout')
            else:
                # Create new address from form fields
                street_address = request.POST.get('street_address', '').strip()
                city = request.POST.get('city', '').strip()
                postal_code = request.POST.get('postal_code', '').strip()
                country = request.POST.get('country', '').strip()
                save_address = request.POST.get('save_address', '0') == '1'
                
                if not all([street_address, city, postal_code, country]):
                    messages.error(request, "Please fill in all required address fields.")
                    return redirect('orders:checkout')
                
                # Get user's full name
                full_name = request.user.get_full_name() or request.user.username
                
                # Only create Address record if user wants to save it
                # Otherwise, we'll just use the text delivery_address
                if save_address:
                    # Create new address and save it to user's addresses
                    order_address = Address.objects.create(
                        user=request.user,
                        full_name=full_name,
                        address_type='shipping',
                        address_line1=street_address,
                        address_line2='',
                        city=city,
                        state=city,  # Use city as state if state not provided
                        postal_code=postal_code,
                        zip_code=postal_code,
                        country=country,
                        is_default=False  # Don't set as default automatically
                    )
                else:
                    # User doesn't want to save address, so we'll just use text version
                    # Set address to None - order will only have delivery_address text
                    order_address = None
            
            # Get voucher code from session
            voucher_code = request.session.get('applied_voucher_code', None)
            voucher = None
            discount_amount = Decimal('0.00')
            
            # Validate and apply voucher if present
            if voucher_code:
                try:
                    from vouchers.utils import apply_voucher_to_cart
                    
                    subtotal_before_voucher = sum(
                        ((item.product_variant.effective_price if item.product_variant else Decimal("0")) * item.quantity).quantize(Decimal("0.01"))
                        for item in cart_items
                    )
                    
                    if subtotal_before_voucher < Decimal(str(settings.FREE_SHIPPING_THRESHOLD)):
                        shipping_before_voucher = Decimal(str(settings.SHIPPING_COST))
                    else:
                        shipping_before_voucher = Decimal("0.00")
                    
                    voucher_result = apply_voucher_to_cart(
                        voucher_code, request.user, cart_items, subtotal_before_voucher, shipping_before_voucher
                    )
                    voucher = voucher_result['voucher']
                    discount_amount = voucher_result['discount_amount']
                except Exception as e:
                    logger.warning(f"Voucher validation failed: {str(e)}")
                    voucher_code = None
                    discount_amount = Decimal('0.00')
            
            # Calculate totals
            totals = calculate_cart_totals(cart_items, voucher_code=voucher_code, user=request.user)
            
            # Extract phone number from shipping address
            phone_match = re.search(r'Phone:\s*(.+?)(?:\n|$)', shipping_address)
            contact_number = phone_match.group(1).strip() if phone_match else ''
            
            # Create order (pending payment)
            order = Order.objects.create(
                user=request.user,
                address=order_address,  # Link to Address model
                delivery_address=shipping_address,  # Keep text version for historical reference
                contact_number=contact_number,
                payment_method=payment_method,
                status='pending',
                subtotal=totals['subtotal'],
                tax=totals['tax'],
                shipping_cost=totals['shipping'],
                voucher_code=voucher_code or '',
                discount_amount=discount_amount,
                total=totals['total'],
                payment_status='pending'
            )
            
            # Create order items and update stock
            for cart_item in cart_items:
                item_price = cart_item.product_variant.effective_price if cart_item.product_variant else Decimal("0")
                
                OrderItem.objects.create(
                    order=order,
                    product=cart_item.product,
                    product_variant=cart_item.product_variant,
                    quantity=cart_item.quantity,
                    price=item_price
                )
                
                # Update product stock (reserve items)
                if cart_item.product_variant:
                    if cart_item.product_variant.stock >= cart_item.quantity:
                        cart_item.product_variant.stock -= cart_item.quantity
                        cart_item.product_variant.save()
                    else:
                        raise ValueError(f"Insufficient stock for {cart_item.product.name}")
                else:
                    if cart_item.product.stock >= cart_item.quantity:
                        cart_item.product.stock -= cart_item.quantity
                        cart_item.product.save()
                    else:
                        raise ValueError(f"Insufficient stock for {cart_item.product.name}")
            
            # Store order ID in session for Stripe checkout
            request.session['pending_order_id'] = order.id
            request.session.modified = True
            
            # Redirect to Stripe checkout
            return redirect('orders:create_stripe_checkout')
            
    except ValueError as ve:
        logger.error(f"Validation error: {str(ve)}")
        messages.error(request, str(ve))
        return redirect('orders:checkout')
    except Exception as e:
        logger.error(f"Checkout error: {str(e)}", exc_info=True)
        messages.error(request, f"An error occurred while processing your order. Please try again.")
        return redirect('orders:checkout')


@login_required
def create_stripe_checkout(request):
    """Create Stripe Checkout Session"""
    order_id = request.session.get('pending_order_id')
    if not order_id:
        messages.error(request, "No pending order found.")
        return redirect('orders:checkout')
    
    try:
        order = Order.objects.get(id=order_id, user=request.user, payment_status='pending')
        
        # Prepare line items for Stripe
        line_items = []
        for item in order.items.all():
            # Build variant description from attributes
            variant_desc = ""
            if item.product_variant:
                variant_attrs = []
                if item.product_variant.color:
                    variant_attrs.append(item.product_variant.color)
                if item.product_variant.size:
                    variant_attrs.append(item.product_variant.size)
                if variant_attrs:
                    variant_desc = f" ({', '.join(variant_attrs)})"
            
            line_items.append({
                'price_data': {
                    'currency': 'usd',
                    'product_data': {
                        'name': item.product.name,
                        'description': f"{item.product.name}{variant_desc} - Qty: {item.quantity}",
                    },
                    'unit_amount': int(item.price * 100),  # Convert to cents
                },
                'quantity': item.quantity,
            })
        
        # Add tax and shipping as separate line items
        if order.tax > 0:
            line_items.append({
                'price_data': {
                    'currency': 'usd',
                    'product_data': {
                        'name': 'Tax',
                    },
                    'unit_amount': int(order.tax * 100),
                },
                'quantity': 1,
            })
        
        if order.shipping_cost > 0:
            line_items.append({
                'price_data': {
                    'currency': 'usd',
                    'product_data': {
                        'name': 'Shipping',
                    },
                    'unit_amount': int(order.shipping_cost * 100),
                },
                'quantity': 1,
            })
        
        # Create Stripe Checkout Session
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=line_items,
            mode='payment',
            success_url=request.build_absolute_uri(reverse('orders:payment_success')) + '?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=request.build_absolute_uri(reverse('orders:payment_cancel')),
            metadata={
                'order_id': str(order.id),
                'user_id': str(request.user.id),
            },
            customer_email=request.user.email,
        )
        
        # Store checkout session ID in order
        order.stripe_payment_intent_id = checkout_session.id
        order.save()
        
        return redirect(checkout_session.url)
        
    except Order.DoesNotExist:
        messages.error(request, "Order not found.")
        return redirect('orders:checkout')
    except Exception as e:
        logger.error(f"Stripe checkout error: {str(e)}", exc_info=True)
        messages.error(request, "Error creating payment session. Please try again.")
        return redirect('orders:checkout')


@login_required
def payment_success(request):
    """Handle successful payment"""
    session_id = request.GET.get('session_id')
    
    if not session_id:
        messages.error(request, "Invalid payment session.")
        return redirect('orders:order_list')
    
    try:
        # Retrieve the checkout session from Stripe
        checkout_session = stripe.checkout.Session.retrieve(session_id)
        order_id = checkout_session.metadata.get('order_id')
        
        if not order_id:
            messages.error(request, "Order information not found.")
            return redirect('orders:order_list')
        
        order = Order.objects.get(id=order_id, user=request.user)
        
        # Verify payment was successful
        if checkout_session.payment_status == 'paid':
            # Update order with payment information but keep status as pending
            order.payment_status = 'paid'
            order.status = 'pending'  # Keep as pending for admin review
            order.stripe_payment_intent_id = checkout_session.payment_intent
            order.stripe_customer_id = checkout_session.customer or ''
            
            # Get payment method type
            if checkout_session.payment_intent:
                payment_intent = stripe.PaymentIntent.retrieve(checkout_session.payment_intent)
                if payment_intent.payment_method:
                    pm = stripe.PaymentMethod.retrieve(payment_intent.payment_method)
                    order.stripe_payment_method = pm.type
                    order.payment_method = pm.type
            
            from django.utils import timezone
            order.paid_at = timezone.now()
            order.save()
            
            # Clear cart
            cart = get_or_create_cart(request)
            cart.items.all().delete()
            
            # Clear pending order from session
            if 'pending_order_id' in request.session:
                del request.session['pending_order_id']
                request.session.modified = True
            
            messages.success(request, f"Payment successful! Order {order.order_number} is pending confirmation.")
            return redirect('orders:order_detail', order_id=order.id)
        else:
            # Payment failed or not completed - restore stock only (items still in cart)
            for order_item in order.items.all():
                # Restore stock
                if order_item.product_variant:
                    order_item.product_variant.stock += order_item.quantity
                    order_item.product_variant.save()
                else:
                    order_item.product.stock += order_item.quantity
                    order_item.product.save()
            
            # Delete the failed order
            order.delete()
            
            # Clear pending order from session
            if 'pending_order_id' in request.session:
                del request.session['pending_order_id']
                request.session.modified = True
            
            messages.error(request, "Payment was not completed. Your items are still in your cart.")
            return redirect('cart:cart_detail')
            
    except Order.DoesNotExist:
        messages.error(request, "Order not found.")
        return redirect('orders:order_list')
    except Exception as e:
        logger.error(f"Payment success error: {str(e)}", exc_info=True)
        messages.error(request, "Error processing payment confirmation.")
        return redirect('orders:order_list')


@login_required
def payment_cancel(request):
    """Handle cancelled payment - redirect back to cart"""
    order_id = request.session.get('pending_order_id')
    
    if order_id:
        try:
            order = Order.objects.get(id=order_id, user=request.user)
            
            # Restore stock (items are still in cart, so no need to restore to cart)
            for order_item in order.items.all():
                # Restore stock
                if order_item.product_variant:
                    order_item.product_variant.stock += order_item.quantity
                    order_item.product_variant.save()
                else:
                    order_item.product.stock += order_item.quantity
                    order_item.product.save()
            
            # Delete the cancelled order
            order.delete()
            messages.info(request, "Payment was cancelled. Your items are still in your cart.")
        except Order.DoesNotExist:
            messages.info(request, "Payment was cancelled.")
        
        # Clear pending order from session
        if 'pending_order_id' in request.session:
            del request.session['pending_order_id']
            request.session.modified = True
    
    return redirect('cart:cart_detail')


@csrf_exempt
def stripe_webhook(request):
    """Handle Stripe webhooks"""
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    
    # Webhook secret is optional - skip verification if not set
    webhook_secret = getattr(settings, 'STRIPE_WEBHOOK_SECRET', '')
    if not webhook_secret:
        # For development: parse event without verification
        try:
            event = json.loads(payload)
        except ValueError:
            logger.error("Invalid payload")
            return HttpResponse(status=400)
    else:
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, webhook_secret
            )
        except ValueError:
            logger.error("Invalid payload")
            return HttpResponse(status=400)
        except stripe.error.SignatureVerificationError:
            logger.error("Invalid signature")
            return HttpResponse(status=400)
    
    # Handle the event
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        order_id = session.metadata.get('order_id')
        
        if order_id:
            try:
                order = Order.objects.get(id=order_id)
                if session.payment_status == 'paid':
                    # Keep order as pending even after payment
                    order.payment_status = 'paid'
                    order.status = 'pending'  # Keep as pending for admin review
                    order.stripe_payment_intent_id = session.payment_intent
                    order.stripe_customer_id = session.customer or ''
                    
                    from django.utils import timezone
                    order.paid_at = timezone.now()
                    order.save()
                    
                    logger.info(f"Order {order.order_number} payment received via webhook (status: pending)")
            except Order.DoesNotExist:
                logger.error(f"Order {order_id} not found in webhook")
    
    return HttpResponse(status=200)


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
    status_counts = {}
    for status, info in status_info.items():
        status_orders = orders.filter(status=status)
        count = status_orders.count()
        status_counts[status] = count
        orders_by_status.append({
            'status': status,
            'info': info,
            'orders': status_orders,
            'count': count
        })

    context = {
        "orders": orders,
        "orders_by_status": orders_by_status,
        "status_info": status_info,
        "status_counts": status_counts,
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
                    logger.info(f"Restored {item.quantity} units of stock for variant ID {item.product_variant.id}")
                else:
                    item.product.stock += item.quantity
                    item.product.save()
                    logger.info(f"Restored {item.quantity} units of stock for product: {item.product.name}")
            
            # Update order status
            order.status = 'cancelled'
            order.save()
            
            logger.info(f"Order {order.order_number} cancelled successfully by user {request.user.username}")
            messages.success(request, f"Order {order.order_number} has been cancelled successfully.")
            
    except Exception as e:
        logger.error(f"Error cancelling order {order.order_number}: {str(e)}", exc_info=True)
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
        
        # Calculate subtotal first (using effective prices)
        from decimal import Decimal
        subtotal = sum(
            ((item.product_variant.effective_price if item.product_variant else Decimal("0")) * item.quantity).quantize(Decimal("0.01"))
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
def get_available_vouchers(request):
    """AJAX endpoint to get available vouchers for the current user"""
    if request.method != 'GET':
        return JsonResponse({'success': False, 'error': 'Invalid request method.'}, status=405)
    
    try:
        from vouchers.models import Voucher, VoucherUsage
        from django.utils import timezone
        from decimal import Decimal
        
        now = timezone.now()
        cart = get_or_create_cart(request)
        cart_items = cart.items.select_related("product", "product_variant").all()
        
        # Calculate current cart subtotal (using effective prices)
        subtotal = sum(
            ((item.product_variant.effective_price if item.product_variant else Decimal("0")) * item.quantity).quantize(Decimal("0.01"))
            for item in cart_items
        )
        
        # Get user-specific vouchers
        user_vouchers = Voucher.objects.filter(
            user=request.user,
            is_active=True,
            start_date__lte=now,
            end_date__gte=now
        ).order_by('-created_at')
        
        # Get public vouchers
        public_vouchers = Voucher.objects.filter(
            user__isnull=True,
            is_active=True,
            start_date__lte=now,
            end_date__gte=now
        ).order_by('-created_at')
        
        # Combine and deduplicate
        all_vouchers = list(user_vouchers) + list(public_vouchers)
        seen_ids = set()
        unique_vouchers = []
        for voucher in all_vouchers:
            if voucher.id not in seen_ids:
                seen_ids.add(voucher.id)
                unique_vouchers.append(voucher)
        
        # Filter vouchers that can be used
        available_vouchers = []
        for voucher in unique_vouchers:
            # Check if voucher meets minimum purchase requirement
            if voucher.min_purchase and subtotal < voucher.min_purchase:
                continue
            
            # Check usage count
            usage_count = VoucherUsage.objects.filter(
                voucher=voucher,
                user=request.user
            ).count()
            
            if usage_count >= voucher.max_uses_per_user:
                continue
            
            # Check if voucher can be used by this user
            if not voucher.can_be_used_by_user(request.user, usage_count=usage_count):
                continue
            
            # Calculate potential discount for display
            discount_info = {
                'type': voucher.discount_type,
                'value': str(voucher.discount_value),
                'max_discount': str(voucher.max_discount) if voucher.max_discount else None,
            }
            
            available_vouchers.append({
                'id': voucher.id,
                'promo_code': voucher.promo_code,
                'name': voucher.name,
                'description': voucher.description or '',
                'discount_type': voucher.discount_type,
                'discount_value': str(voucher.discount_value),
                'max_discount': str(voucher.max_discount) if voucher.max_discount else None,
                'min_purchase': str(voucher.min_purchase) if voucher.min_purchase else None,
                'remaining_uses': max(0, voucher.max_uses_per_user - usage_count),
            })
        
        return JsonResponse({
            'success': True,
            'vouchers': available_vouchers,
            'cart_subtotal': str(subtotal),
        })
        
    except Exception as e:
        logger.error(f"Error fetching vouchers: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'Failed to fetch vouchers.'
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