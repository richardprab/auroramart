from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.db import transaction
from django.db.models import (
    Q,
    Sum,
    F,
    IntegerField,
    Count,
    Avg,
    ExpressionWrapper,
    DurationField,
)
from django.db.models.functions import Coalesce, TruncDate
from django.core.files.base import ContentFile
from django.template.loader import render_to_string
from django.core.paginator import Paginator
from urllib.parse import quote
from functools import wraps
from django.urls import reverse
from django.conf import settings
from django.contrib import messages
from pathlib import Path
import os
import io
from contextlib import redirect_stdout
import requests
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
import csv
import logging
import traceback

logger = logging.getLogger(__name__)

from products.models import Product, ProductVariant, ProductImage, Category
from accounts.models import User, Staff, Customer, BrowsingHistory
from chat.models import ChatConversation, ChatMessage
from orders.models import Order, OrderItem
from vouchers.models import Voucher
from notifications.models import Notification
from .forms import ProductSearchForm, OrderSearchForm, VoucherForm, StaffSearchForm, StaffPermissionForm, CustomerSearchForm
from django.views.decorators.http import require_POST


LOW_STOCK_THRESHOLD = 5
PENDING_ORDER_STATUSES = ['pending', 'confirmed', 'processing']
REVENUE_STATUSES = ['pending', 'confirmed', 'processing', 'shipped', 'delivered']
FULFILLMENT_EXCLUDED_STATUSES = ['cancelled', 'refunded']


def _paginate_request_collection(request, collection, per_page=10, page_param='page'):
    """
    Returns a Django Page object for the provided collection using request GET params.
    """
    paginator = Paginator(collection, per_page)
    page_number = request.GET.get(page_param)
    return paginator.get_page(page_number)


def _build_pagination_querystring(request, page_param='page'):
    """
    Builds an encoded querystring (prefixed with &) that preserves current filters sans page.
    """
    query_params = request.GET.copy()
    if page_param in query_params:
        query_params.pop(page_param)
    encoded = query_params.urlencode()
    return f'&{encoded}' if encoded else ''


def _get_required_permission(path):
    """
    Map URL paths to required permissions.
    Returns the permission string needed for the given path, or None if no specific permission is required.
    """
    if '/products/' in path:
        return 'products'
    elif '/orders/' in path:
        return 'orders'
    elif '/customer-support/' in path or '/chat/' in path:
        return 'chat'
    elif '/analytics/' in path:
        return 'analytics'
    elif '/staff/' in path:
        # Staff management requires superuser, handled separately
        return None
    # Dashboard, vouchers, database management don't require specific permissions
    # (but still require staff access)
    return None


def staff_login_required(view_func):
    """
    Custom decorator that requires staff authentication and checks permissions.
    Redirects to staff login page if not authenticated or not staff.
    Automatically logs out Customer users and redirects them to customer login.
    Checks permissions for Staff users (superusers always have access).
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            login_url = reverse('adminpanel:staff_login')
            return redirect(f'{login_url}?next={request.path}')
        
        # Check if user is a Customer - if so, log them out and redirect
        from accounts.models import Customer
        if isinstance(request.user, Customer):
            from django.contrib.auth import logout
            from django.contrib import messages
            logout(request)
            messages.info(request, 'Customer accounts cannot access admin panel. Please use the customer login page.')
            return redirect('/accounts/login/')
        
        if not request.user.is_staff and not request.user.is_superuser:
            from django.contrib import messages
            messages.error(request, 'You do not have permission to access this page.')
            return redirect('adminpanel:dashboard')
        
        # Superusers always have access
        if request.user.is_superuser:
            return view_func(request, *args, **kwargs)
        
        # For Staff users, check permissions
        from accounts.models import Staff
        if isinstance(request.user, Staff):
            required_permission = _get_required_permission(request.path)
            
            # If a specific permission is required, check if staff has it
            if required_permission:
                if not request.user.has_permission(required_permission):
                    # Map permission names to friendly names
                    permission_names = {
                        'products': 'Product Management',
                        'orders': 'Order Management',
                        'chat': 'Customer Support/Chat',
                        'analytics': 'Analytics',
                    }
                    friendly_name = permission_names.get(required_permission, required_permission)
                    
                    # Render permission denied page
                    return render(request, 'adminpanel/permission_denied.html', {
                        'feature_name': friendly_name,
                    })
        
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def staff_login(request):
    """
    Staff login - allows Staff users and Superusers to login and access admin panel.
    Only Staff users and Superusers can login through this endpoint.
    Customer users are automatically logged out if they try to access this page.
    """
    # If a Customer user is logged in, log them out and redirect
    from accounts.models import Customer, Superuser
    if request.user.is_authenticated:
        if isinstance(request.user, Customer):
            from django.contrib.auth import logout
            from django.contrib import messages
            logout(request)
            messages.info(request, 'Customer accounts cannot access admin panel. Please use the customer login page.')
            return redirect('/accounts/login/')
        elif request.user.is_staff or request.user.is_superuser:
            return redirect('/adminpanel/')
    
    from django.contrib.auth import login
    from django.contrib import messages
    from django.contrib.auth.backends import ModelBackend
    
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        
        if not username or not password:
            messages.error(request, 'Please provide both username and password.')
            return render(request, 'adminpanel/staff_login.html')
        
        user = None
        is_superuser = False
        
        # Try to find Superuser first (since they should have priority)
        try:
            user = Superuser.objects.get(username=username)
            is_superuser = True
        except Superuser.DoesNotExist:
            try:
                user = Superuser.objects.get(email=username)
                is_superuser = True
            except Superuser.DoesNotExist:
                # Try to find Staff user by username
                try:
                    user = Staff.objects.get(username=username)
                except Staff.DoesNotExist:
                    # Also try to find by email in case user entered email
                    try:
                        user = Staff.objects.get(email=username)
                    except Staff.DoesNotExist:
                        messages.error(request, 'Invalid credentials. Staff/Superuser access only.')
                        return render(request, 'adminpanel/staff_login.html')
        
        # Verify password
        password_valid = user.check_password(password)
        if not password_valid:
            messages.error(request, 'Invalid credentials. Please check your username and password.')
            return render(request, 'adminpanel/staff_login.html')
        
        if not user.is_active:
            messages.error(request, 'Your account is inactive. Please contact an administrator.')
            return render(request, 'adminpanel/staff_login.html')
        
        # Ensure is_staff and is_superuser are set correctly
        if is_superuser:
            if not user.is_superuser:
                user.is_superuser = True
            if not user.is_staff:
                user.is_staff = True
            user.save()
        else:
            # For Staff users, ensure is_staff is True
            if not user.is_staff:
                user.is_staff = True
                user.save()
        
        # Use the appropriate custom backend
        if is_superuser:
            # For Superusers, use the SuperuserModelBackend
            backend = 'accounts.backends.SuperuserModelBackend'
        else:
            # For Staff users, use the StaffModelBackend
            backend = 'accounts.backends.StaffModelBackend'
        
        # Refresh the user from database to ensure we have the latest state
        user.refresh_from_db()
        
        # Log in the user
        login(request, user, backend=backend)
        
        # Verify login was successful
        if request.user.is_authenticated and (request.user.is_staff or request.user.is_superuser):
            # Always redirect to admin panel root (/adminpanel/)
            return redirect('/adminpanel/')
        else:
            messages.error(request, 'Login failed. Please try again.')
    
    return render(request, 'adminpanel/staff_login.html', {
        'next': request.GET.get('next', '')
    })


def get_next_assigned_staff():
    """
    Round-robin assignment of staff members.
    Returns the next staff member to be assigned based on ascending staff number.
    """
    # Get all staff users ordered by username (staff001, staff002, etc.)
    # Staff must have 'chat' permission to be assigned conversations
    staff_users = Staff.objects.filter(
        is_active=True,
        permissions__in=['all', 'chat', 'products,chat', 'orders,chat', 'products,orders,chat']
    ).order_by('username')
    
    if not staff_users.exists():
        return None
    
    # Get the last assigned conversation
    last_conversation = ChatConversation.objects.filter(admin__isnull=False).order_by('-created_at').first()
    
    if not last_conversation or not last_conversation.admin:
        # No previous assignment, assign to first staff
        return staff_users.first()
    
    # Find the next staff member in the list
    current_staff = last_conversation.admin
    staff_list = list(staff_users)
    
    try:
        current_index = staff_list.index(current_staff)
        next_index = (current_index + 1) % len(staff_list)
        return staff_list[next_index]
    except ValueError:
        # Current staff not found, assign to first
        return staff_list[0]

# ==================== DASHBOARD ====================

@staff_login_required
def dashboard(request):
    """Main admin dashboard with overview metrics"""
    
    # Get stats
    total_products = Product.objects.count()
    pending_orders = Order.objects.filter(status__in=['pending', 'confirmed', 'processing']).count()
    
    # For superusers, show all pending conversations. For staff, show only their assigned ones.
    if request.user.is_superuser:
        my_open_conversations = ChatConversation.objects.filter(
            status='pending'
        ).count()
    else:
        # For Staff users, filter by admin
        from accounts.models import Staff
        if isinstance(request.user, Staff):
            my_open_conversations = ChatConversation.objects.filter(
                admin=request.user,
                status='pending'
            ).count()
        else:
            my_open_conversations = 0
    
    low_stock_count = Product.objects.annotate(
        total_stock=Coalesce(Sum('variants__stock'), 0, output_field=IntegerField())
    ).filter(total_stock__lt=LOW_STOCK_THRESHOLD).count()
    
    # Recent orders
    recent_orders = Order.objects.select_related('user').order_by('-created_at')[:5]
    
    context = {
        'total_products': total_products,
        'pending_orders': pending_orders,
        'open_conversations': my_open_conversations,
        'low_stock_count': low_stock_count,
        'recent_orders': recent_orders,
    }
    
    return render(request, 'adminpanel/dashboard.html', context)

# ==================== CUSTOMER ASSISTANCE ====================

@staff_login_required
def customer_support(request):
    """List all messages assigned to current staff member"""
    
    # Get filter parameter
    filter_status = request.GET.get('status', 'all')
    
    # For superusers, show all conversations. For staff, show only their assigned ones.
    if request.user.is_superuser:
        # Superusers can see all conversations
        conversations = ChatConversation.objects.all().select_related('user', 'product', 'admin').prefetch_related('messages')
    else:
        # For Staff users, filter by admin
        from accounts.models import Staff
        if isinstance(request.user, Staff):
            conversations = ChatConversation.objects.filter(
                admin=request.user
            ).select_related('user', 'product', 'admin').prefetch_related('messages')
        else:
            conversations = ChatConversation.objects.none()
    
    # Apply status filter
    if filter_status == 'pending':
        conversations = conversations.filter(status='pending')
    elif filter_status == 'replied':
        conversations = conversations.filter(status='replied')
    
    # Order by oldest first (as requested)
    conversations = conversations.order_by('created_at')
    
    # Get latest order for each customer
    for conv in conversations:
        conv.latest_order = Order.objects.filter(user=conv.user).order_by('-created_at').first()
    
    context = {
        'conversations': conversations,
        'filter_status': filter_status,
    }
    
    return render(request, 'adminpanel/customer_support.html', context)

@staff_login_required
def chat_conversation(request, conversation_id):
    """View and reply to a specific customer message"""
    
    # For superusers, allow access to all conversations. For staff, only their assigned ones.
    if request.user.is_superuser:
        conversation = get_object_or_404(
            ChatConversation.objects.select_related('user', 'product', 'admin'),
            id=conversation_id
        )
    else:
        # For Staff users, only allow access to their assigned conversations
        from accounts.models import Staff
        if isinstance(request.user, Staff):
            conversation = get_object_or_404(
                ChatConversation.objects.select_related('user', 'product', 'admin'),
                id=conversation_id,
                admin=request.user
            )
        else:
            from django.http import HttpResponseForbidden
            return HttpResponseForbidden('You do not have permission to access this conversation.')
    
    # Get all messages in this conversation
    messages_list = conversation.messages.select_related('sender', 'staff_sender').order_by('created_at')
    
    # Get customer's latest order
    latest_order = Order.objects.filter(user=conversation.user).order_by('-created_at').first()
    
    # Handle reply submission
    if request.method == 'POST':
        content = request.POST.get('message')
        if content:
            # Create new message (staff/superuser sending reply)
            from accounts.models import Staff
            if isinstance(request.user, Staff):
                ChatMessage.objects.create(
                    conversation=conversation,
                    staff_sender=request.user,
                    content=content
                )
            elif request.user.is_superuser:
                # For superusers, we can't use staff_sender (requires Staff) or sender (requires Customer)
                # So we'll create the message with both fields as None - the content will still be saved
                # The message will be attributed to the conversation admin or shown as system message
                ChatMessage.objects.create(
                    conversation=conversation,
                    content=content,
                    sender=None,
                    staff_sender=None
                )
            
            # Update conversation status to 'replied'
            conversation.status = 'replied'
            conversation.user_has_unread = True
            conversation.admin_has_unread = False
            conversation.save()
            
            from django.urls import reverse
            url = reverse('adminpanel:chat_conversation', args=[conversation_id]) + '?replied=1'
            return redirect(url)
    
    # Mark admin messages as read
    conversation.admin_has_unread = False
    conversation.save()
    
    context = {
        'conversation': conversation,
        'messages': messages_list,
        'latest_order': latest_order,
    }
    
    return render(request, 'adminpanel/chat_conversation.html', context)

# ==================== PRODUCT MANAGEMENT ====================

def _get_primary_image_url(product):
    """
    Helper to retrieve a product's primary image URL, falling back gracefully.
    """
    try:
        primary_image = product.images.filter(is_primary=True).first()
        if primary_image and primary_image.image:
            return primary_image.image.url
        fallback = product.images.first()
        if fallback and fallback.image:
            return fallback.image.url
    except Exception:
        return ''
    return ''


@staff_login_required
def product_management(request):
    """Product search and management page"""
    # Initialize form with query from GET parameters if present
    # Support both 'q' and 'query' for backward compatibility
    initial_query = request.GET.get('query', request.GET.get('q', ''))
    form = ProductSearchForm(initial={'query': initial_query})
    
    # Load initial products if query is provided, otherwise show all
    products_data = []
    if initial_query:
        # Use the search logic from search_product view
        search_q = (
            Q(name__icontains=initial_query) | 
            Q(slug__icontains=initial_query) | 
            Q(sku__icontains=initial_query) | 
            Q(variants__sku__icontains=initial_query) |
            Q(description__icontains=initial_query) |
            Q(category__name__icontains=initial_query)
        )
        all_products = Product.objects.filter(search_q).distinct().prefetch_related(
            'images', 'category', 'reviews__user', 'variants'
        )[:100]
        
        # Sort by relevance (simplified version)
        def get_relevance_score(product):
            query_lower = initial_query.lower().strip()
            product_sku_lower = (product.sku.lower() if product.sku else '').strip()
            product_name_lower = (product.name.lower() if product.name else '').strip()
            variant_skus = [v.sku.lower().strip() for v in product.variants.all() if v.sku and v.sku.strip()]
            
            if product_sku_lower == query_lower or query_lower in variant_skus:
                return 5
            if product_sku_lower and product_sku_lower.startswith(query_lower):
                return 4
            if any(sku.startswith(query_lower) for sku in variant_skus):
                return 4
            if product_name_lower and product_name_lower.startswith(query_lower):
                return 3
            if product_name_lower == query_lower:
                return 2
            return 1
        
        all_products = sorted(all_products, key=lambda p: (-get_relevance_score(p), p.name.lower()))
        products = list(all_products)[:50]
    else:
        products = Product.objects.all().prefetch_related(
            'images', 'category', 'reviews__user', 'variants'
        ).order_by('name')[:50]
    
    # Prepare product data for template
    for product in products:
        try:
            primary_image_url = _get_primary_image_url(product)
            
            total_stock = sum(variant.stock for variant in product.variants.all())
            reviews = product.reviews.select_related('user').all()[:5]
            
            rating_stars = ''
            if product.rating and product.rating > 0:
                rating_int = int(round(float(product.rating)))
                rating_stars = '★' * rating_int + '☆' * (5 - rating_int)
            
            products_data.append({
                'product': product,
                'primary_image_url': primary_image_url,
                'total_stock': total_stock,
                'reviews': reviews,
                'rating_stars': rating_stars,
            })
        except Exception:
            continue
    
    products_page_obj = _paginate_request_collection(request, products_data, per_page=10)
    products_extra_query = _build_pagination_querystring(request)

    low_stock_queryset = Product.objects.annotate(
        total_stock=Coalesce(Sum('variants__stock'), 0, output_field=IntegerField())
    ).filter(total_stock__lt=LOW_STOCK_THRESHOLD).select_related('category').prefetch_related('images').order_by('total_stock', 'name')

    low_stock_products = []
    for product in low_stock_queryset[:25]:
        low_stock_products.append({
            'id': product.id,
            'name': product.name,
            'sku': product.sku,
            'category': product.category.name if product.category else 'Uncategorized',
            'total_stock': product.total_stock or 0,
            'reorder_quantity': product.reorder_quantity,
            'image': _get_primary_image_url(product),
        })

    context = {
        'form': form,
        'search_query': initial_query,
        'products_page_obj': products_page_obj,
        'products_extra_query': products_extra_query,
        'low_stock_products': low_stock_products,
        'low_stock_threshold': LOW_STOCK_THRESHOLD,
    }
    return render(request, 'adminpanel/products.html', context)


@staff_login_required
@require_POST
def reorder_product(request, product_id):
    """Replenish a product's variants by its configured reorder quantity."""
    product = get_object_or_404(Product.objects.prefetch_related('variants', 'category'), pk=product_id)
    reorder_qty = product.reorder_quantity

    if reorder_qty <= 0:
        message = "This product has no reorder quantity configured."
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'status': 'error', 'message': message}, status=400)
        messages.error(request, message)
        return redirect('adminpanel:products')

    variants = product.variants.all()
    if not variants.exists():
        message = "This product has no variants to restock."
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'status': 'error', 'message': message}, status=400)
        messages.error(request, message)
        return redirect('adminpanel:products')

    with transaction.atomic():
        variant_count = variants.count()
        current_total = variants.aggregate(
            total=Coalesce(Sum('stock'), 0, output_field=IntegerField())
        )['total'] or 0

        variants.update(stock=F('stock') + reorder_qty)
        total_added = reorder_qty * variant_count
        new_total = current_total + total_added

    success_message = f"Restock placed for {product.name}. Added {total_added} units."

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({
            'status': 'success',
            'message': success_message,
            'new_total_stock': new_total,
            'added_amount': total_added,
            'product_id': product.id,
        })

    messages.success(request, success_message)
    return redirect('adminpanel:products')

@staff_login_required
def search_product(request):
    """AJAX endpoint to search for products and return HTML table rendered server-side"""
    query = request.GET.get('query', '').strip()
    
    try:
        # If empty query, return all products
        if not query:
            all_products = Product.objects.all().prefetch_related(
                'images', 
                'category',
                'reviews__user',
                'variants'
            ).order_by('name')[:50]
        else:
            # Build search query with priority for exact matches
            # Priority order:
            # 1. Exact SKU match (product or variant) - highest priority (5)
            # 2. SKU starts with query (4)
            # 3. Name starts with query (3) - NEW - this fixes "Car" search
            # 4. Exact name/slug match (2)
            # 5. Partial matches/contains (1)
            
            # Get all products that match any condition
            search_q = (
                Q(name__icontains=query) | 
                Q(slug__icontains=query) | 
                Q(sku__icontains=query) | 
                Q(variants__sku__icontains=query) |
                Q(description__icontains=query) |
                Q(category__name__icontains=query)
            )
            
            # Get all matching products
            all_products = Product.objects.filter(
                search_q
            ).distinct().prefetch_related(
                'images', 
                'category',
                'reviews__user',
                'variants'
            )[:100]  # Get more to sort, then limit
            
            # Sort products by relevance
            def get_relevance_score(product):
                query_lower = query.lower().strip()
                product_sku_lower = (product.sku.lower() if product.sku else '').strip()
                product_name_lower = (product.name.lower() if product.name else '').strip()
                product_slug_lower = (product.slug.lower() if product.slug else '').strip()
                
                # Check variant SKUs - need to access prefetched variants
                variant_skus = []
                try:
                    variant_skus = [v.sku.lower().strip() for v in product.variants.all() if v.sku and v.sku.strip()]
                except Exception:
                    pass
                
                # Priority 5: Exact SKU match (product or variant) - highest priority
                if product_sku_lower == query_lower:
                    return 5
                if query_lower in variant_skus:
                    return 5
                
                # Priority 4: SKU starts with query
                if product_sku_lower and product_sku_lower.startswith(query_lower):
                    return 4
                if any(sku.startswith(query_lower) for sku in variant_skus):
                    return 4
                
                # Priority 3: Name starts with query - THIS FIXES "Car" search issue
                if product_name_lower and product_name_lower.startswith(query_lower):
                    return 3
                
                # Priority 2: Exact name or slug match
                if product_name_lower == query_lower or product_slug_lower == query_lower:
                    return 2
                
                # Priority 1: Partial match (contains but doesn't start with)
                return 1
            
            # Sort by relevance (higher first), then by name
            all_products = sorted(all_products, key=lambda p: (-get_relevance_score(p), p.name.lower()))
        
        products = list(all_products)[:50]
        
        # Prepare product data for template
        products_data = []
        for product in products:
            try:
                # Get primary image URL
                primary_image_url = ''
                try:
                    primary_image = product.images.filter(is_primary=True).first()
                    if primary_image and primary_image.image:
                        primary_image_url = primary_image.image.url
                    else:
                        first_image = product.images.first()
                        if first_image and first_image.image:
                            primary_image_url = first_image.image.url
                except Exception:
                    pass
                
                # Get total stock from variants
                total_stock = sum(variant.stock for variant in product.variants.all())
                
                # Get reviews (limit to 5 most recent)
                reviews = product.reviews.select_related('user').all()[:5]
                
                # Compute rating stars for display
                rating_stars = ''
                if product.rating and product.rating > 0:
                    rating_int = int(round(float(product.rating)))
                    rating_stars = '★' * rating_int + '☆' * (5 - rating_int)
                
                products_data.append({
                    'product': product,
                    'primary_image_url': primary_image_url,
                    'total_stock': total_stock,
                    'reviews': reviews,
                    'rating_stars': rating_stars,
                })
            except Exception as e:
                # Skip products that cause errors
                logger.error(f"Error processing product {product.id}: {str(e)}")
                continue
        
        products_page_obj = _paginate_request_collection(request, products_data, per_page=10)
        extra_query = _build_pagination_querystring(request)
        
        # Render table HTML using Django template
        table_html = render_to_string(
            'adminpanel/includes/product_table.html',
            {
                'products': products_page_obj,
                'page_obj': products_page_obj,
                'extra_query': extra_query,
                'search_query': query,
            },
            request=request
        )
        
        # Return HTML response
        return HttpResponse(table_html)
    
    except Exception as e:
        logger.error(f"Error in search_product: {str(e)}\n{traceback.format_exc()}")
        return HttpResponse(
            '<div class="error-message">An error occurred while searching products. Please try again.</div>',
            status=500
        )

@staff_login_required
def edit_product(request, product_id):
    """Display product edit form"""
    product = get_object_or_404(
        Product.objects.prefetch_related('images', 'variants', 'category', 'reviews__user'),
        id=product_id
    )
    
    # Get search query from request if coming from search page
    # Support both 'q' and 'query' for backward compatibility
    search_query = request.GET.get('q', request.GET.get('query', ''))
    
    # Get conversation ID if coming from chat
    from_chat = request.GET.get('from_chat', '')
    
    # Get primary image
    primary_image = product.images.filter(is_primary=True).first()
    primary_image_url = ''
    try:
        if primary_image and primary_image.image:
            primary_image_url = primary_image.image.url
    except Exception:
        # If image doesn't exist or can't be accessed, use empty string
        pass
    
    # Get all categories for dropdown
    categories = Category.objects.all().order_by('name')
    
    context = {
        'product': product,
        'primary_image_url': primary_image_url,
        'categories': categories,
        'search_query': search_query,
        'from_chat': from_chat,
    }
    
    return render(request, 'adminpanel/edit_product.html', context)

@staff_login_required
def update_product(request):
    """Update product details and redirect back to edit page"""
    if request.method != 'POST':
        return redirect('adminpanel:products')
    
    try:
        product_id = request.POST.get('product_id')
        product = get_object_or_404(Product, id=product_id)
        
        # Get search query to preserve it in redirect
        search_query = request.POST.get('search_query', '')
        
        # Get from_chat parameter to preserve it in redirect
        from_chat = request.POST.get('from_chat', '')
        
        # Update basic product info
        product.name = request.POST.get('name', product.name)
        product.description = request.POST.get('description', product.description)
        
        # Update category if provided
        category_id = request.POST.get('category_id')
        if category_id:
            try:
                category = Category.objects.get(id=category_id)
                product.category = category
            except Category.DoesNotExist:
                pass
        
        product.save()
        
        # Handle product main image
        product_image_url = request.POST.get('product_image_url', '').strip()
        product_image_file = request.FILES.get('product_image_file')
        
        if product_image_file:
            # File upload takes priority
            primary_image = product.images.filter(is_primary=True).first()
            if primary_image:
                primary_image.image = product_image_file
                primary_image.save()
            else:
                ProductImage.objects.create(
                    product=product,
                    image=product_image_file,
                    is_primary=True
                )
        elif product_image_url and product_image_url.startswith('http'):
            # URL provided - download and save
            try:
                response = requests.get(product_image_url, timeout=10)
                if response.status_code == 200:
                    file_name = product_image_url.split('/')[-1]
                    primary_image = product.images.filter(is_primary=True).first()
                    if primary_image:
                        primary_image.image.save(file_name, ContentFile(response.content), save=True)
                    else:
                        img = ProductImage.objects.create(product=product, is_primary=True)
                        img.image.save(file_name, ContentFile(response.content), save=True)
            except Exception as e:
                logger.error(f"Error downloading product image: {e}")
        
        # Update variants
        variant_ids = request.POST.getlist('variant_id[]')
        
        for index, variant_id in enumerate(variant_ids):
            try:
                variant = ProductVariant.objects.get(id=variant_id)
                
                # Update variant fields
                variant_stock = request.POST.get(f'variant_stock_{index}')
                variant_price = request.POST.get(f'variant_price_{index}')
                
                if variant_stock:
                    variant.stock = int(variant_stock)
                if variant_price:
                    variant.price = float(variant_price)
                
                variant.save()
                        
            except ProductVariant.DoesNotExist:
                continue
            except Exception as e:
                logger.error(f"Error updating variant {variant_id}: {e}")
                continue
        
        # Add success message and redirect back to edit page with search query
        from django.contrib import messages
        from django.urls import reverse
        messages.success(request, 'Product updated successfully!')
        
        # Redirect back to edit product page with preserved parameters
        edit_url = reverse('adminpanel:edit_product', kwargs={'product_id': product_id})
        params = []
        
        if from_chat:
            params.append(f'from_chat={from_chat}')
        if search_query:
            params.append(f'q={quote(search_query)}')
        
        if params:
            return redirect(f'{edit_url}?{"&".join(params)}')
        else:
            return redirect('adminpanel:edit_product', product_id=product_id)
        
    except Exception as e:
        logger.error(f"Error updating product: {str(e)}\n{traceback.format_exc()}")
        messages.error(request, f'Error updating product: {str(e)}')
        return redirect('adminpanel:edit_product', product_id=product_id)

# ==================== ORDER MANAGEMENT ====================

@staff_login_required
def order_management(request):
    """Order search and management page"""
    # Initialize form with query from GET parameters if present
    # Support both 'q' and 'query' for backward compatibility
    initial_query = request.GET.get('query', request.GET.get('q', ''))
    form = OrderSearchForm(initial={'query': initial_query})
    
    # Load initial orders if query is provided, otherwise show recent orders
    orders_data = []
    if initial_query:
        query_upper = initial_query.upper()
        
        # Determine if query looks like an order number
        is_likely_order_number = query_upper.startswith('ORD')
        
        if is_likely_order_number:
            # Search by order number
            search_q = Q(order_number__icontains=initial_query)
            if not query_upper.startswith('ORD'):
                search_q |= Q(order_number__icontains=f'ORD-{initial_query}')
            
            matching_orders = Order.objects.filter(search_q).select_related('user').prefetch_related('items__product_variant__product').distinct()[:100]
            
            # Sort by relevance
            def get_relevance_score(order):
                order_num_upper = order.order_number.upper()
                if order_num_upper == query_upper or order_num_upper == f'ORD-{query_upper}':
                    return 5
                if order_num_upper.startswith(query_upper) or order_num_upper.startswith(f'ORD-{query_upper}'):
                    return 4
                if query_upper in order_num_upper:
                    return 3
                return 2
            
            matching_orders = sorted(matching_orders, key=lambda o: (-get_relevance_score(o), -o.created_at.timestamp()))
            orders = list(matching_orders)[:50]
            
            for order in orders:
                orders_data.append({
                    'order': order,
                    'search_type': 'order',
                })
        else:
            # Search by customer (search across Customer, Staff, Superuser)
            from accounts.models import Customer, Staff, Superuser
            query_filter = Q(username__icontains=initial_query) | Q(email__icontains=initial_query) | Q(first_name__icontains=initial_query) | Q(last_name__icontains=initial_query)
            customers = Customer.objects.filter(query_filter)[:20]
            staff = Staff.objects.filter(query_filter)[:20]
            superusers = Superuser.objects.filter(query_filter)[:20]
            # Combine results (limit to 20 total)
            matching_users = list(customers) + list(staff) + list(superusers)
            matching_users = matching_users[:20]
            
            for user in matching_users:
                user_orders = Order.objects.filter(user=user).select_related('user').prefetch_related('items__product_variant__product').order_by('-created_at')[:10]
                for order in user_orders:
                    orders_data.append({
                        'order': order,
                        'search_type': 'customer',
                    })
            
            # Sort by created_at (most recent first)
            orders_data.sort(key=lambda x: x['order'].created_at, reverse=True)
            orders_data = orders_data[:50]
    else:
        # Show recent orders
        orders = Order.objects.select_related('user').prefetch_related('items__product_variant__product').order_by('-created_at')[:50]
        for order in orders:
            orders_data.append({
                'order': order,
                'search_type': 'order',
            })
    
    pending_orders_queryset = Order.objects.filter(
        status='pending'
    ).select_related('user').order_by('created_at')

    pending_orders_alert = []
    for order in pending_orders_queryset[:25]:
        customer_name = order.user.get_full_name() or order.user.username if order.user else 'Guest'
        pending_orders_alert.append({
            'id': order.id,
            'order_number': order.order_number,
            'customer_name': customer_name,
            'username': order.user.username if order.user else '',
            'status': order.status,
            'status_display': order.get_status_display(),
            'total': order.total,
            'created_at': order.created_at,
        })

    orders_page_obj = _paginate_request_collection(request, orders_data, per_page=10)
    orders_extra_query = _build_pagination_querystring(request)

    context = {
        'form': form,
        'search_query': initial_query,
        'orders_page_obj': orders_page_obj,
        'orders_extra_query': orders_extra_query,
        'pending_orders_alert': pending_orders_alert,
        'pending_orders_count': pending_orders_queryset.count(),
        'pending_statuses': PENDING_ORDER_STATUSES,
    }
    return render(request, 'adminpanel/order_management.html', context)

@staff_login_required
def search_order(request):
    """AJAX endpoint to search for orders and return HTML table rendered server-side"""
    query = request.GET.get('query', '').strip()
    
    try:
        orders_data = []
        
        if not query:
            # If empty query, return recent orders (limit to 50)
            orders = (
                Order.objects.select_related('user')
                .prefetch_related('items__product_variant__product')
                .order_by('-created_at')[:50]
            )
            for order in orders:
                orders_data.append({
                    'order': order,
                    'search_type': 'order',
                })
        else:
            query_upper = query.upper()
            # Determine if query looks like an order number (starts with ORD)
            is_likely_order_number = query_upper.startswith('ORD')
            
            if is_likely_order_number:
                # Search by order number with fuzzy matching
                search_q = Q(order_number__icontains=query)
                
                # Try with ORD prefix if query doesn't have it
                if not query_upper.startswith('ORD'):
                    search_q |= Q(order_number__icontains=f'ORD-{query}')
                
                matching_orders = Order.objects.filter(
                    search_q
                ).select_related('user').prefetch_related('items__product_variant__product').distinct()[:100]
                
                # Sort by relevance
                def get_relevance_score(order):
                    order_num_upper = order.order_number.upper()
                    
                    # Priority 5: Exact match
                    if order_num_upper == query_upper:
                        return 5
                    if order_num_upper == f'ORD-{query_upper}':
                        return 5
                    
                    # Priority 4: Starts with query
                    if order_num_upper.startswith(query_upper):
                        return 4
                    if order_num_upper.startswith(f'ORD-{query_upper}'):
                        return 4
                    
                    # Priority 3: Contains query
                    if query_upper in order_num_upper:
                        return 3
                    
                    # Priority 2: Partial match
                    return 2
                
                # Sort by relevance (higher first), then by created_at (newest first)
                matching_orders = sorted(matching_orders, key=lambda o: (-get_relevance_score(o), -o.created_at.timestamp()))
                
                for order in matching_orders[:50]:  # Limit to 50 results
                    orders_data.append({
                        'order': order,
                        'search_type': 'order',
                    })
            else:
                # Search by customer username
                # Get all users matching the query (search across Customer, Staff, Superuser)
                from accounts.models import Customer, Staff, Superuser
                query_filter = Q(username__icontains=query) | Q(email__icontains=query) | Q(first_name__icontains=query) | Q(last_name__icontains=query)
                customers = Customer.objects.filter(query_filter)[:20]
                staff = Staff.objects.filter(query_filter)[:20]
                superusers = Superuser.objects.filter(query_filter)[:20]
                # Combine results (limit to 20 total)
                matching_users = list(customers) + list(staff) + list(superusers)
                matching_users = matching_users[:20]
                
                # For each user, get their most recent orders
                for user in matching_users:
                    user_orders = Order.objects.filter(user=user).select_related('user').prefetch_related('items__product_variant__product').order_by('-created_at')[:10]
                    
                    for order in user_orders:
                        orders_data.append({
                            'order': order,
                            'search_type': 'customer',
                        })
                
                # Sort by created_at (most recent first)
                orders_data.sort(key=lambda x: x['order'].created_at, reverse=True)
                orders_data = orders_data[:50]  # Limit to 50 results
        
        orders_page_obj = _paginate_request_collection(request, orders_data, per_page=10)
        extra_query = _build_pagination_querystring(request)
        
        # Render table HTML using Django template
        table_html = render_to_string(
            'adminpanel/includes/order_table.html',
            {
                'orders': orders_page_obj,
                'page_obj': orders_page_obj,
                'extra_query': extra_query,
                'search_query': query,
            },
            request=request
        )
        
        # Return HTML response
        return HttpResponse(table_html)
    
    except Exception as e:
        logger.error(f"Error in search_order: {str(e)}\n{traceback.format_exc()}")
        return HttpResponse(
            '<div class="error-message">An error occurred while searching orders. Please try again.</div>',
            status=500
        )

@staff_login_required
def edit_order(request, order_id):
    """Display order edit form"""
    order = get_object_or_404(
        Order.objects.select_related('user', 'address').prefetch_related('items__product_variant__product'),
        id=order_id
    )
    
    # Get search query from request if coming from search page
    # Support both 'q' and 'query' for backward compatibility
    search_query = request.GET.get('q', request.GET.get('query', ''))
    
    # Get all available variants for order editing
    all_variants = ProductVariant.objects.filter(stock__gt=0).select_related('product')
    
    # Calculate current location index and progress for tracking visualization
    current_location_index = None
    progress_percentage = 0
    total_locations = len(Order.LOCATION_CHOICES)
    
    for index, (value, label) in enumerate(Order.LOCATION_CHOICES):
        if order.current_location == value:
            current_location_index = index
            # Calculate progress percentage for the tracking line
            # With space-between layout, dots are evenly distributed from 0% to 100%
            # Progress extends from left edge to center of active dot
            if total_locations > 1:
                # Calculate position: (index / (total - 1)) * 100
                # But ensure minimum visibility for first step
                if index == 0:
                    progress_percentage = 8  # Show small progress for first step
                else:
                    progress_percentage = (index / (total_locations - 1)) * 100
            else:
                progress_percentage = 50
            break
    
    context = {
        'order': order,
        'search_query': search_query,
        'all_variants': all_variants,
        'location_choices': Order.LOCATION_CHOICES,
        'status_choices': Order.STATUS_CHOICES,
        'current_location_index': current_location_index,
        'progress_percentage': progress_percentage,
    }
    
    return render(request, 'adminpanel/edit_order.html', context)

@staff_login_required
def update_order(request, order_id):
    """Update order details and redirect back to edit page"""
    if request.method != 'POST':
        return redirect('adminpanel:order_management')
    
    try:
        order = get_object_or_404(Order, id=order_id)
        
        # Get search query to preserve it in redirect
        search_query = request.POST.get('search_query', '')
        
        # Update current location
        current_location = request.POST.get('current_location')
        if current_location:
            order.current_location = current_location
        
        # Update status
        status = request.POST.get('status')
        if status:
            order.status = status
        
        # Only allow editing contact and address if order is pending/confirmed/processing
        if order.status in ['pending', 'confirmed', 'processing']:
            contact_number = request.POST.get('contact_number')
            delivery_address = request.POST.get('delivery_address')
            
            if contact_number:
                order.contact_number = contact_number
            if delivery_address:
                order.delivery_address = delivery_address
        
        order.save()
        
        # Add success message and redirect back to edit page with search query
        from django.contrib import messages
        from django.urls import reverse
        messages.success(request, 'Order updated successfully!')
        
        # Redirect back to edit order page with search query if provided
        if search_query:
            edit_url = reverse('adminpanel:edit_order', kwargs={'order_id': order_id})
            return redirect(f'{edit_url}?q={quote(search_query)}')
        else:
            return redirect('adminpanel:edit_order', order_id=order_id)
        
    except Exception as e:
        logger.error(f"Error in update_order: {str(e)}\n{traceback.format_exc()}")
        messages.error(request, f'Error updating order: {str(e)}')
        return redirect('adminpanel:edit_order', order_id=order_id)

# ==================== ANALYTICS ====================

@staff_login_required
def analytics(request):
    """Analytics dashboard with live metrics"""
    return render(request, 'adminpanel/analytics.html')


def _format_currency(value):
    return f"${value:,.2f}"


def _safe_percentage(numerator, denominator):
    if not denominator:
        return 0.0
    return float(numerator) / float(denominator)


def _format_duration(seconds):
    if seconds is None:
        return "—"
    seconds = int(seconds)
    if seconds < 60:
        return f"{seconds}s"
    minutes, sec = divmod(seconds, 60)
    if minutes < 60:
        return f"{minutes}m {sec}s"
    hours, minutes = divmod(minutes, 60)
    if hours < 24:
        return f"{hours}h {minutes}m"
    days, hours = divmod(hours, 24)
    return f"{days}d {hours}h"


def _build_analytics_payload(days=14):
    days = max(7, min(90, int(days)))
    now = timezone.now()
    start_date = (now - timedelta(days=days - 1)).date()

    daily_qs = (
        Order.objects.filter(
            created_at__date__gte=start_date,
            status__in=REVENUE_STATUSES
        )
        .annotate(day=TruncDate('created_at'))
        .values('day')
        .annotate(
            revenue=Coalesce(Sum('total'), Decimal('0')),
            orders=Count('id')
        )
        .order_by('day')
    )

    daily_map = {item['day']: item for item in daily_qs}
    timeseries = []
    highlights = []
    prev_revenue = None
    change_threshold = 0.25

    for offset in range(days):
        day = start_date + timedelta(days=offset)
        metrics = daily_map.get(day, {'revenue': Decimal('0'), 'orders': 0})
        revenue = metrics.get('revenue') or Decimal('0')
        orders = metrics.get('orders') or 0
        change_pct = 0.0
        warning = False

        if prev_revenue is not None and prev_revenue > 0:
            change_pct = float((revenue - prev_revenue) / prev_revenue)
            if abs(change_pct) >= change_threshold:
                warning = True
                highlights.append({
                    'label': 'Revenue spike' if change_pct > 0 else 'Revenue dip',
                    'description': f"{day.strftime('%b %d')}: {change_pct:+.0%} vs prior day",
                    'direction': 'up' if change_pct > 0 else 'down',
                })

        timeseries.append({
            'date': day.isoformat(),
            'date_label': day.strftime('%b %d'),
            'revenue': float(revenue),
            'orders': orders,
            'change_pct': change_pct,
            'warning': warning,
        })

        prev_revenue = revenue

    lookback_days = 30
    period_start = now - timedelta(days=lookback_days)
    previous_period_start = period_start - timedelta(days=lookback_days)

    recent_orders_qs = Order.objects.filter(
        created_at__gte=period_start,
        status__in=REVENUE_STATUSES
    )
    recent_revenue = recent_orders_qs.aggregate(total=Coalesce(Sum('total'), Decimal('0')))['total']
    recent_revenue = recent_revenue or Decimal('0')
    recent_order_count = recent_orders_qs.count()

    prev_orders_qs = Order.objects.filter(
        created_at__gte=previous_period_start,
        created_at__lt=period_start,
        status__in=REVENUE_STATUSES
    )
    prev_revenue = prev_orders_qs.aggregate(total=Coalesce(Sum('total'), Decimal('0')))['total']
    prev_revenue = prev_revenue or Decimal('0')

    revenue_change = 0.0
    if prev_revenue > 0:
        revenue_change = float((recent_revenue - prev_revenue) / prev_revenue)

    avg_order_value = float(recent_revenue / recent_order_count) if recent_order_count else 0.0

    delivered_count = Order.objects.filter(status='delivered').count()
    active_orders = Order.objects.exclude(status__in=FULFILLMENT_EXCLUDED_STATUSES).count()
    fulfillment_rate = _safe_percentage(delivered_count, active_orders)

    visit_count = BrowsingHistory.objects.filter(viewed_at__gte=period_start).count()

    customer_orders = Order.objects.exclude(user__isnull=True).values('user').annotate(order_count=Count('id'))
    repeat_customers = customer_orders.filter(order_count__gt=1).count()
    unique_customers = customer_orders.count()
    repeat_rate = _safe_percentage(repeat_customers, unique_customers)

    pending_orders = Order.objects.filter(status__in=PENDING_ORDER_STATUSES).count()
    conversion_rate = _safe_percentage(recent_order_count, visit_count)

    conversations = ChatConversation.objects.filter(
        created_at__gte=period_start
    ).prefetch_related('messages__sender', 'messages__staff_sender')
    response_total = timedelta()
    response_samples = 0
    for conv in conversations:
        first_customer_msg = None
        for msg in conv.messages.all():
            if msg.staff_sender:
                if first_customer_msg:
                    delta = msg.created_at - first_customer_msg
                    if delta.total_seconds() >= 0:
                        response_total += delta
                        response_samples += 1
                    break
            else:
                if first_customer_msg is None:
                    first_customer_msg = msg.created_at
    avg_response_seconds = None
    if response_samples:
        avg_response_seconds = (response_total / response_samples).total_seconds()

    cycle_queryset = Order.objects.filter(
        status='delivered',
        delivered_at__isnull=False,
        delivered_at__gte=period_start,
    ).annotate(
        cycle=ExpressionWrapper(F('delivered_at') - F('created_at'), output_field=DurationField())
    )
    avg_cycle = cycle_queryset.aggregate(avg_cycle=Avg('cycle'))['avg_cycle']
    avg_cycle_seconds = avg_cycle.total_seconds() if avg_cycle else None

    summary = {
        'revenue_30d': {
            'value': float(recent_revenue),
            'display': _format_currency(float(recent_revenue)),
            'change_pct': revenue_change,
            'context': f"{revenue_change:+.1%} vs prior 30 days" if revenue_change else "No prior data",
            'alert': revenue_change < -0.2,
        },
        'avg_order_value': {
            'value': avg_order_value,
            'display': _format_currency(avg_order_value),
            'context': f"{recent_order_count} orders last 30 days",
            'alert': avg_order_value < 30,
        },
        'conversion_rate': {
            'value': conversion_rate,
            'display': f"{conversion_rate:.1%}",
            'context': f"{recent_order_count} orders / {visit_count or 0} visits",
            'alert': conversion_rate < 0.02 and visit_count > 100,
        },
        'repeat_customer_rate': {
            'value': repeat_rate,
            'display': f"{repeat_rate:.0%}",
            'context': f"{repeat_customers} repeat shoppers of {unique_customers}",
            'alert': repeat_rate < 0.25 and unique_customers > 20,
        },
        'fulfillment_rate': {
            'value': fulfillment_rate,
            'display': f"{fulfillment_rate:.0%}",
            'context': f"{delivered_count} delivered / {active_orders} active orders",
            'alert': fulfillment_rate < 0.9 and active_orders > 0,
        },
        'pending_orders': {
            'value': pending_orders,
            'display': f"{pending_orders} awaiting action",
            'context': "Pending, confirmed, or processing",
            'alert': pending_orders > 40,
        },
        'chat_response_time': {
            'value': avg_response_seconds or 0,
            'display': _format_duration(avg_response_seconds),
            'context': f"Avg. from customer ping to staff reply ({response_samples} samples)",
            'alert': avg_response_seconds is not None and avg_response_seconds > 3600,
        },
        'order_cycle_time': {
            'value': avg_cycle_seconds or 0,
            'display': _format_duration(avg_cycle_seconds),
            'context': "Creation to delivery for recent fulfilled orders",
            'alert': avg_cycle_seconds is not None and avg_cycle_seconds > 7 * 24 * 3600,
        },
    }

    status_mix_raw = Order.objects.values('status').annotate(count=Count('id')).order_by('-count')
    total_orders = sum(item['count'] for item in status_mix_raw) or 1
    status_mix = [{
        'status': item['status'],
        'count': item['count'],
        'percentage': round((item['count'] / total_orders) * 100, 1),
    } for item in status_mix_raw]

    recent_items = (
        OrderItem.objects.filter(
            order__created_at__gte=period_start,
            order__status__in=REVENUE_STATUSES
        )
        .values('product__name', 'product__sku')
        .annotate(quantity=Sum('quantity'))
        .order_by('-quantity')[:5]
    )
    prev_items = (
        OrderItem.objects.filter(
            order__created_at__gte=previous_period_start,
            order__created_at__lt=period_start,
            order__status__in=REVENUE_STATUSES
        )
        .values('product__name', 'product__sku')
        .annotate(quantity=Sum('quantity'))
    )
    prev_map = {}
    for item in prev_items:
        key = item['product__sku'] or item['product__name']
        prev_map[key] = item['quantity'] or 0

    product_insights = []
    for item in recent_items:
        key = item['product__sku'] or item['product__name']
        qty = item['quantity'] or 0
        prev_qty = prev_map.get(key, 0)
        change = qty - prev_qty
        change_pct = None
        if prev_qty:
            change_pct = _safe_percentage(change, prev_qty)
        product_insights.append({
            'name': item['product__name'] or 'Unnamed product',
            'sku': item['product__sku'] or '',
            'orders': int(qty),
            'change_pct': change_pct,
            'direction': 'up' if change >= 0 else 'down',
        })

    return {
        'timeseries': timeseries,
        'summary': summary,
        'trend_highlights': highlights,
        'status_mix': status_mix,
        'product_insights': product_insights,
        'updated_at': now.isoformat(),
    }


@staff_login_required
def analytics_data(request):
    days = request.GET.get('days', 14)
    payload = _build_analytics_payload(days)
    return JsonResponse(payload)


@staff_login_required
def analytics_export(request):
    days = request.GET.get('days', 30)
    payload = _build_analytics_payload(days)
    response = HttpResponse(content_type='text/csv')
    filename = f"auroramart-analytics-{timezone.now().strftime('%Y%m%d-%H%M%S')}.csv"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    writer = csv.writer(response)
    writer.writerow(['Date', 'Revenue', 'Orders'])
    for row in payload['timeseries']:
        writer.writerow([row['date'], f"{row['revenue']:.2f}", row['orders']])

    return response

# ==================== VOUCHER MANAGEMENT ====================

@staff_login_required
def voucher_management(request):
    """Voucher management page - list all vouchers"""
    vouchers = Voucher.objects.all().order_by('-created_at')
    
    vouchers_page_obj = _paginate_request_collection(request, vouchers, per_page=10)
    vouchers_extra_query = _build_pagination_querystring(request)
    
    context = {
        'vouchers_page_obj': vouchers_page_obj,
        'vouchers_extra_query': vouchers_extra_query,
    }
    return render(request, 'adminpanel/voucher_management.html', context)

@staff_login_required
def add_voucher(request):
    """Add a new voucher"""
    if request.method == 'POST':
        form = VoucherForm(request.POST)
        if form.is_valid():
            voucher = form.save(commit=False)
            # Set created_by if user is a superuser
            if hasattr(request.user, 'is_superuser') and request.user.is_superuser:
                voucher.created_by = request.user
            voucher.save()
            form.save_m2m()  # Save many-to-many relationships
            
            from django.contrib import messages
            messages.success(request, f'Voucher "{voucher.name}" created successfully!')
            return redirect('adminpanel:voucher_management')
    else:
        form = VoucherForm()
    
    context = {
        'form': form,
        'action': 'Add',
    }
    return render(request, 'adminpanel/voucher_form.html', context)

@staff_login_required
def edit_voucher(request, voucher_id):
    """Edit an existing voucher"""
    voucher = get_object_or_404(Voucher, id=voucher_id)
    
    if request.method == 'POST':
        form = VoucherForm(request.POST, instance=voucher)
        if form.is_valid():
            form.save()
            
            from django.contrib import messages
            messages.success(request, f'Voucher "{voucher.name}" updated successfully!')
            return redirect('adminpanel:voucher_management')
    else:
        form = VoucherForm(instance=voucher)
    
    context = {
        'form': form,
        'voucher': voucher,
        'action': 'Edit',
    }
    return render(request, 'adminpanel/voucher_form.html', context)

@staff_login_required
def delete_voucher(request, voucher_id):
    """Delete a voucher"""
    voucher = get_object_or_404(Voucher, id=voucher_id)
    
    if request.method == 'POST':
        voucher_name = voucher.name
        voucher.delete()
        
        from django.contrib import messages
        messages.success(request, f'Voucher "{voucher_name}" deleted successfully!')
        return redirect('adminpanel:voucher_management')
    
    context = {
        'voucher': voucher,
    }
    return render(request, 'adminpanel/delete_voucher.html', context)


# ==================== STAFF MANAGEMENT ====================

def superuser_required(view_func):
    """
    Decorator that requires superuser authentication.
    Only superusers can access staff management pages.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            login_url = reverse('adminpanel:staff_login')
            return redirect(f'{login_url}?next={request.path}')
        
        # Check if user is a Customer - if so, log them out and redirect
        from accounts.models import Customer
        if isinstance(request.user, Customer):
            from django.contrib.auth import logout
            from django.contrib import messages
            logout(request)
            messages.info(request, 'Customer accounts cannot access admin panel. Please use the customer login page.')
            return redirect('/accounts/login/')
        
        if not request.user.is_superuser:
            feature_name_map = {
                'database_management': 'Database Management',
                'run_populate_db': 'Database Management',
                'staff_management': 'Staff Management',
                'search_staff': 'Staff Management',
                'edit_staff': 'Staff Management',
                'update_staff': 'Staff Management',
            }
            feature_name = feature_name_map.get(view_func.__name__, 'This Feature')
            return render(request, 'adminpanel/permission_denied.html', {
                'feature_name': feature_name,
            })
        
        return view_func(request, *args, **kwargs)
    return _wrapped_view


@superuser_required
def database_management(request):
    """Database management page for populating and managing database"""
    project_root = Path(settings.BASE_DIR)
    csv_files = []
    data_dir = project_root / 'data'
    
    if data_dir.exists():
        csv_files = [f.name for f in data_dir.glob('*.csv')]
    
    context = {
        'csv_files': csv_files,
    }
    return render(request, 'adminpanel/database_management.html', context)


@superuser_required
def staff_management(request):
    """Staff search and management page - only accessible to superusers"""
    # Initialize form with query from GET parameters if present
    initial_query = request.GET.get('query', request.GET.get('q', ''))
    form = StaffSearchForm(initial={'query': initial_query})
    
    # Load initial staff if query is provided, otherwise show all
    staff_data = []
    if initial_query:
        # Search by username or email
        search_q = (
            Q(username__icontains=initial_query) | 
            Q(email__icontains=initial_query) |
            Q(first_name__icontains=initial_query) |
            Q(last_name__icontains=initial_query)
        )
        staff_list = Staff.objects.filter(search_q).order_by('username')[:50]
    else:
        staff_list = Staff.objects.all().order_by('username')[:50]
    
    # Prepare staff data for template
    for staff in staff_list:
        # Get permission display name
        permissions_display = staff.permissions
        for choice_value, choice_label in Staff.PERMISSION_CHOICES:
            if choice_value == staff.permissions:
                permissions_display = choice_label
                break
        
        staff_data.append({
            'staff': staff,
            'permissions_display': permissions_display,
        })
    
    context = {
        'form': form,
        'search_query': initial_query,
        'staff_data': staff_data,
        'permission_choices': Staff.PERMISSION_CHOICES,
    }
    return render(request, 'adminpanel/staff_management.html', context)


@superuser_required
def search_staff(request):
    """AJAX endpoint to search for staff and return HTML table rendered server-side"""
    query = request.GET.get('query', '').strip()
    
    try:
        # If empty query, return all staff
        if not query:
            staff_list = Staff.objects.all().order_by('username')[:50]
        else:
            # Search by username or email
            search_q = (
                Q(username__icontains=query) | 
                Q(email__icontains=query) |
                Q(first_name__icontains=query) |
                Q(last_name__icontains=query)
            )
            staff_list = Staff.objects.filter(search_q).order_by('username')[:50]
        
        # Prepare staff data for template
        staff_data = []
        for staff in staff_list:
            # Get permission display name
            permissions_display = staff.permissions
            for choice_value, choice_label in Staff.PERMISSION_CHOICES:
                if choice_value == staff.permissions:
                    permissions_display = choice_label
                    break
            
            staff_data.append({
                'staff': staff,
                'permissions_display': permissions_display,
            })
        
        # Render table HTML using Django template
        table_html = render_to_string(
            'adminpanel/includes/staff_table.html',
            {
                'staff_data': staff_data,
                'search_query': query,
                'permission_choices': Staff.PERMISSION_CHOICES,
            },
            request=request
        )
        
        # Return HTML response
        return HttpResponse(table_html)
    
    except Exception as e:
        logger.error(f"Error in search_staff: {str(e)}\n{traceback.format_exc()}")
        return HttpResponse(
            '<div class="error-message">An error occurred while searching staff. Please try again.</div>',
            status=500
        )


@superuser_required
def edit_staff(request, staff_id):
    """Display staff edit form for permissions"""
    staff = get_object_or_404(Staff, id=staff_id)
    
    # Get search query from request if coming from search page
    search_query = request.GET.get('q', request.GET.get('query', ''))
    
    # Initialize form with current permissions
    initial_data = {}
    if staff.permissions == 'all':
        initial_data['all_permissions'] = True
    else:
        permission_list = [p.strip() for p in staff.permissions.split(',')]
        for perm in permission_list:
            if perm in ['products', 'orders', 'chat', 'analytics']:
                initial_data[perm] = True
    
    form = StaffPermissionForm(initial=initial_data)
    
    context = {
        'staff': staff,
        'form': form,
        'search_query': search_query,
        'permission_choices': Staff.PERMISSION_CHOICES,
    }
    
    return render(request, 'adminpanel/edit_staff.html', context)


@superuser_required
@require_POST
def update_staff(request, staff_id):
    """Update staff permissions and redirect back to edit page"""
    staff = get_object_or_404(Staff, id=staff_id)
    
    # Get search query to preserve it in redirect
    search_query = request.POST.get('search_query', '')
    
    form = StaffPermissionForm(request.POST)
    
    if form.is_valid():
        staff.permissions = form.cleaned_data['permissions']
        staff.save()
        from django.contrib import messages
        from django.urls import reverse
        messages.success(request, f'Staff permissions for {staff.username} updated successfully!')
        
        # Redirect back to staff management page with search query if provided
        if search_query:
            return redirect(f'{reverse("adminpanel:staff_management")}?q={quote(search_query)}')
        else:
            return redirect('adminpanel:staff_management')
    else:
        from django.contrib import messages
        messages.error(request, 'Error updating staff permissions. Please try again.')
        return redirect('adminpanel:edit_staff', staff_id=staff_id)


@staff_login_required
def customer_management(request):
    """Customer search and management page"""
    # Initialize form with query from GET parameters if present
    initial_query = request.GET.get('query', request.GET.get('q', ''))
    form = CustomerSearchForm(initial={'query': initial_query})
    
    # Load initial customers if query is provided, otherwise show recent customers
    customers_data = []
    if initial_query:
        # Search by username, email, first_name, or last_name
        search_q = (
            Q(username__icontains=initial_query) | 
            Q(email__icontains=initial_query) |
            Q(first_name__icontains=initial_query) |
            Q(last_name__icontains=initial_query)
        )
        customers = Customer.objects.filter(search_q).order_by('-date_joined')[:50]
    else:
        customers = Customer.objects.all().order_by('-date_joined')[:50]
    
    # Prepare customer data for template
    for customer in customers:
        # Get order count
        order_count = Order.objects.filter(user=customer).count()
        
        # Get total spent
        total_spent = Order.objects.filter(
            user=customer,
            status__in=['delivered', 'shipped']
        ).aggregate(total=Sum('total'))['total'] or Decimal('0.00')
        
        customers_data.append({
            'customer': customer,
            'order_count': order_count,
            'total_spent': total_spent,
        })
    
    customers_page_obj = _paginate_request_collection(request, customers_data, per_page=10)
    customers_extra_query = _build_pagination_querystring(request)
    
    context = {
        'form': form,
        'search_query': initial_query,
        'customers_page_obj': customers_page_obj,
        'customers_extra_query': customers_extra_query,
    }
    return render(request, 'adminpanel/customer_management.html', context)


@staff_login_required
def search_customer(request):
    """AJAX endpoint to search for customers and return HTML table rendered server-side"""
    query = request.GET.get('query', '').strip()
    
    try:
        # If empty query, return recent customers
        if not query:
            customers = Customer.objects.all().order_by('-date_joined')[:50]
        else:
            # Search by username, email, first_name, or last_name
            search_q = (
                Q(username__icontains=query) | 
                Q(email__icontains=query) |
                Q(first_name__icontains=query) |
                Q(last_name__icontains=query)
            )
            customers = Customer.objects.filter(search_q).order_by('-date_joined')[:50]
        
        # Prepare customer data for template
        customers_data = []
        for customer in customers:
            # Get order count
            order_count = Order.objects.filter(user=customer).count()
            
            # Get total spent
            total_spent = Order.objects.filter(
                user=customer,
                status__in=['delivered', 'shipped']
            ).aggregate(total=Sum('total'))['total'] or Decimal('0.00')
            
            customers_data.append({
                'customer': customer,
                'order_count': order_count,
                'total_spent': total_spent,
            })
        
        # Render table HTML using Django template
        table_html = render_to_string(
            'adminpanel/includes/customer_table.html',
            {
                'customers': customers_data,
                'search_query': query,
            },
            request=request
        )
        
        # Return HTML response
        return HttpResponse(table_html)
    
    except Exception as e:
        logger.error(f"Error in search_customer: {str(e)}\n{traceback.format_exc()}")
        return HttpResponse(
            '<div class="error-message">An error occurred while searching customers. Please try again.</div>',
            status=500
        )


@staff_login_required
def view_customer(request, customer_id):
    """View customer profile details"""
    customer = get_object_or_404(Customer, id=customer_id)
    
    # Get customer orders
    orders = Order.objects.filter(user=customer).order_by('-created_at')[:10]
    
    # Get order statistics
    total_orders = Order.objects.filter(user=customer).count()
    total_spent = Order.objects.filter(
        user=customer,
        status__in=['delivered', 'shipped']
    ).aggregate(total=Sum('total'))['total'] or Decimal('0.00')
    
    # Get search query from request if coming from search page
    search_query = request.GET.get('q', request.GET.get('query', ''))
    
    context = {
        'customer': customer,
        'orders': orders,
        'total_orders': total_orders,
        'total_spent': total_spent,
        'search_query': search_query,
    }
    
    return render(request, 'adminpanel/view_customer.html', context)


@staff_login_required
@require_POST
def suspend_customer(request, customer_id):
    """Suspend or unsuspend a customer account"""
    customer = get_object_or_404(Customer, id=customer_id)
    
    # Get search query to preserve it in redirect
    search_query = request.POST.get('search_query', '')
    
    # Toggle is_active status
    customer.is_active = not customer.is_active
    customer.save()
    
    action = 'suspended' if not customer.is_active else 'unsuspended'
    messages.success(request, f'Customer {customer.username} has been {action} successfully!')
    
    # Redirect back to customer management page with search query if provided
    if search_query:
        return redirect(f'{reverse("adminpanel:customer_management")}?q={quote(search_query)}')
    else:
        return redirect('adminpanel:customer_management')


@superuser_required
def run_populate_db(request):
    """Execute populate_db functions via AJAX"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=405)
    
    action = request.POST.get('action')
    csv_file = request.POST.get('csv_file', 'b2c_products_500.csv')
    reset = request.POST.get('reset', 'true').lower() == 'true'
    
    # Get project root directory
    project_root = Path(settings.BASE_DIR)
    csv_path = project_root / 'data' / csv_file
    
    # Capture stdout to get output from populate_db functions
    output = io.StringIO()
    
    try:
        # Import populate_db functions
        # We need to import them in a way that doesn't trigger django.setup() again
        import importlib.util
        populate_db_path = project_root / 'populate_db.py'
        
        if not populate_db_path.exists():
            return JsonResponse({'error': 'populate_db.py not found'}, status=404)
        
        # Load the module
        spec = importlib.util.spec_from_file_location("populate_db", populate_db_path)
        populate_db = importlib.util.module_from_spec(spec)
        
        # Temporarily redirect stdout to capture print statements
        with redirect_stdout(output):
            # Execute the module (this will run django.setup() but it's safe if already set up)
            spec.loader.exec_module(populate_db)
            
            # Execute the requested action
            if action == 'seed_from_csv':
                if not csv_path.exists():
                    return JsonResponse({'error': f'CSV file not found: {csv_path}'}, status=404)
                
                # Change to project root directory for relative paths
                original_cwd = os.getcwd()
                try:
                    os.chdir(project_root)
                    populate_db.seed_from_csv(str(csv_path), reset=reset)
                finally:
                    os.chdir(original_cwd)
                
            elif action == 'delete_all_data':
                populate_db.delete_all_data()
                
            elif action == 'create_staff_user':
                populate_db.create_staff_user()
                
            elif action == 'create_sample_users':
                populate_db.create_sample_users()
                
            elif action == 'create_sample_orders_and_reviews':
                populate_db.create_sample_orders_and_reviews()
                
            elif action == 'create_nus_computing_tshirt':
                populate_db.create_nus_computing_tshirt()
                
            elif action == 'assign_profile_completion_vouchers':
                populate_db.assign_profile_completion_vouchers()
                
            elif action == 'create_adminpanel_analytics_data':
                populate_db.create_adminpanel_analytics_data()
                
            elif action == 'create_everything':
                reset = request.POST.get('reset', 'true').lower() == 'true'
                csv_path = project_root / 'data' / 'b2c_products_500.csv'
                
                if not csv_path.exists():
                    return JsonResponse({'error': f'CSV file not found: {csv_path}'}, status=404)
                
                original_cwd = os.getcwd()
                try:
                    os.chdir(project_root)
                    populate_db.seed_from_csv(str(csv_path), reset=reset)
                finally:
                    os.chdir(original_cwd)
                
            else:
                return JsonResponse({'error': f'Unknown action: {action}'}, status=400)
        
        output_text = output.getvalue()
        
        return JsonResponse({
            'success': True,
            'message': f'Action "{action}" completed successfully',
            'output': output_text
        })
        
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        return JsonResponse({
            'success': False,
            'error': str(e),
            'traceback': error_trace,
            'output': output.getvalue()
        }, status=500)


@staff_login_required
def send_notification(request):
    """Send notifications to customers from admin panel. Only accessible by staff or managers."""
    # Additional permission check - ensure user is staff or superuser
    if not request.user.is_staff and not request.user.is_superuser:
        messages.error(request, 'You do not have permission to send notifications.')
        return redirect('adminpanel:dashboard')
    
    # Check if Staff user has permission (superusers always have access)
    if isinstance(request.user, Staff) and not request.user.is_superuser:
        # Staff users can send notifications (no specific permission required for notifications)
        pass
    
    if request.method == 'POST':
        recipient_type = request.POST.get('recipient_type', 'selected')
        selected_users = request.POST.getlist('selected_users')
        message = request.POST.get('message', '').strip()
        notification_type = request.POST.get('notification_type', 'platform')
        
        if not message:
            messages.error(request, 'Please enter a notification message.')
        else:
            try:
                users_to_notify = []
                
                if recipient_type == 'all':
                    # Send to all customers (not staff/superusers)
                    users_to_notify = Customer.objects.all()
                elif recipient_type == 'selected' and selected_users:
                    # Send to selected customers
                    users_to_notify = Customer.objects.filter(pk__in=selected_users)
                else:
                    messages.error(request, 'Please select at least one user or choose "All Users".')
                    return redirect('adminpanel:send_notification')
                
                # Create notifications one by one to ensure WebSocket is sent correctly
                # Using create_notification with send_websocket=True ensures proper WebSocket delivery
                count = 0
                for user in users_to_notify:
                    Notification.create_notification(
                        user=user,
                        message=message,
                        notification_type=notification_type,
                        link=None,
                        send_websocket=True
                    )
                    count += 1
                
                messages.success(request, f'Notification sent to {count} customer(s)!')
                
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': True,
                        'message': f'Notification sent to {count} customer(s)'
                    })
            except Exception as e:
                messages.error(request, f'Error sending notification: {str(e)}')
        
        return redirect('adminpanel:send_notification')
    
    # Get all customers for selection (not staff/superusers)
    users = Customer.objects.all().order_by('username')
    total_users = users.count()
    
    context = {
        'users': users,
        'total_users': total_users,
        'notification_types': Notification.NOTIFICATION_TYPES,
    }
    return render(request, 'adminpanel/send_notification.html', context)


