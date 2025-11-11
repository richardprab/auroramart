from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpResponse
from django.db.models import Q
from django.core.files.base import ContentFile
from django.template.loader import render_to_string
from urllib.parse import quote
import requests

from products.models import Product, ProductVariant, ProductImage, Category
from accounts.models import User, Staff
from chat.models import ChatConversation, ChatMessage
from orders.models import Order
from .forms import ProductSearchForm, OrderSearchForm


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

@staff_member_required
def dashboard(request):
    """Main admin dashboard with overview metrics"""
    
    # Get stats
    total_products = Product.objects.count()
    pending_orders = Order.objects.filter(status__in=['pending', 'confirmed', 'processing']).count()
    my_open_conversations = ChatConversation.objects.filter(
        admin=request.user,
        status='pending'
    ).count()
    
    # Recent orders
    recent_orders = Order.objects.select_related('user').order_by('-created_at')[:5]
    
    context = {
        'total_products': total_products,
        'pending_orders': pending_orders,
        'open_conversations': my_open_conversations,
        'recent_orders': recent_orders,
    }
    
    return render(request, 'adminpanel/dashboard.html', context)

# ==================== CUSTOMER ASSISTANCE ====================

@staff_member_required
def customer_support(request):
    """List all messages assigned to current staff member"""
    
    # Get filter parameter
    filter_status = request.GET.get('status', 'all')
    
    # Base queryset - only messages assigned to this staff
    conversations = ChatConversation.objects.filter(
        admin=request.user
    ).select_related('user', 'product', 'admin').prefetch_related('messages')
    
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

@staff_member_required
def chat_conversation(request, conversation_id):
    """View and reply to a specific customer message"""
    
    conversation = get_object_or_404(
        ChatConversation.objects.select_related('user', 'product', 'admin'),
        id=conversation_id,
        admin=request.user  # Ensure staff can only access their assigned messages
    )
    
    # Get all messages in this conversation
    messages_list = conversation.messages.select_related('sender').order_by('created_at')
    
    # Get customer's latest order
    latest_order = Order.objects.filter(user=conversation.user).order_by('-created_at').first()
    
    # Handle reply submission
    if request.method == 'POST':
        content = request.POST.get('message')
        if content:
            # Create new message
            ChatMessage.objects.create(
                conversation=conversation,
                sender=request.user,
                content=content
            )
            
            # Update conversation status to 'replied'
            conversation.status = 'replied'
            conversation.user_has_unread = True
            conversation.admin_has_unread = False
            conversation.save()
            
            return redirect('adminpanel:chat_conversation', conversation_id=conversation_id)
    
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

@staff_member_required
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
    
    context = {
        'form': form,
        'search_query': initial_query,
        'products_data': products_data,
    }
    return render(request, 'adminpanel/products.html', context)

@staff_member_required
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
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Error processing product {product.id}: {str(e)}")
                continue
        
        # Render table HTML using Django template
        table_html = render_to_string(
            'adminpanel/includes/product_table.html',
            {
                'products': products_data,
                'search_query': query,
            },
            request=request
        )
        
        # Return HTML response
        return HttpResponse(table_html)
    
    except Exception as e:
        import logging
        import traceback
        logger = logging.getLogger(__name__)
        logger.error(f"Error in search_product: {str(e)}\n{traceback.format_exc()}")
        return HttpResponse(
            '<div class="error-message">❌ An error occurred while searching products. Please try again.</div>',
            status=500
        )

@staff_member_required
def edit_product(request, product_id):
    """Display product edit form"""
    product = get_object_or_404(
        Product.objects.prefetch_related('images', 'variants', 'category', 'reviews__user'),
        id=product_id
    )
    
    # Get search query from request if coming from search page
    # Support both 'q' and 'query' for backward compatibility
    search_query = request.GET.get('q', request.GET.get('query', ''))
    
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
    }
    
    return render(request, 'adminpanel/edit_product.html', context)

@staff_member_required
def update_product(request):
    """Update product details and redirect back to edit page"""
    if request.method != 'POST':
        return redirect('adminpanel:products')
    
    try:
        product_id = request.POST.get('product_id')
        product = get_object_or_404(Product, id=product_id)
        
        # Get search query to preserve it in redirect
        search_query = request.POST.get('search_query', '')
        
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
                print(f"Error downloading product image: {e}")
        
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
                print(f"Error updating variant {variant_id}: {e}")
                continue
        
        # Add success message and redirect back to edit page with search query
        from django.contrib import messages
        from django.urls import reverse
        messages.success(request, 'Product updated successfully!')
        
        # Redirect back to edit product page with search query if provided
        if search_query:
            edit_url = reverse('adminpanel:edit_product', kwargs={'product_id': product_id})
            return redirect(f'{edit_url}?q={quote(search_query)}')
        else:
            return redirect('adminpanel:edit_product', product_id=product_id)
        
    except Exception as e:
        print(f"Error in update_product: {e}")
        import traceback
        traceback.print_exc()
        # Redirect to edit page with error message
        from django.contrib import messages
        messages.error(request, f'Error updating product: {str(e)}')
        return redirect('adminpanel:edit_product', product_id=product_id)

# ==================== ORDER MANAGEMENT ====================

@staff_member_required
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
        is_likely_order_number = query_upper.startswith('ORD') or (len(initial_query) >= 4 and initial_query.replace('-', '').replace('_', '').isalnum())
        
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
    
    context = {
        'form': form,
        'search_query': initial_query,
        'orders_data': orders_data,
    }
    return render(request, 'adminpanel/order_management.html', context)

@staff_member_required
def search_order(request):
    """AJAX endpoint to search for orders and return HTML table rendered server-side"""
    query = request.GET.get('query', '').strip()
    
    try:
        orders_data = []
        
        if not query:
            # If empty query, return recent orders (limit to 50)
            orders = Order.objects.select_related('user').prefetch_related('items__product_variant__product').order_by('-created_at')[:50]
            for order in orders:
                orders_data.append({
                    'order': order,
                    'search_type': 'order',
                })
        else:
            query_upper = query.upper()
            
            # Determine if query looks like an order number (starts with ORD or is alphanumeric)
            is_likely_order_number = query_upper.startswith('ORD') or (len(query) >= 4 and query.replace('-', '').replace('_', '').isalnum())
            
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
        
        # Render table HTML using Django template
        table_html = render_to_string(
            'adminpanel/includes/order_table.html',
            {
                'orders': orders_data,
                'search_query': query,
            },
            request=request
        )
        
        # Return HTML response
        return HttpResponse(table_html)
    
    except Exception as e:
        import logging
        import traceback
        logger = logging.getLogger(__name__)
        logger.error(f"Error in search_order: {str(e)}\n{traceback.format_exc()}")
        return HttpResponse(
            '<div class="error-message">❌ An error occurred while searching orders. Please try again.</div>',
            status=500
        )

@staff_member_required
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

@staff_member_required
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
        print(f"Error in update_order: {e}")
        import traceback
        traceback.print_exc()
        # Redirect to edit page with error message
        from django.contrib import messages
        messages.error(request, f'Error updating order: {str(e)}')
        return redirect('adminpanel:edit_order', order_id=order_id)

# ==================== ANALYTICS ====================

@staff_member_required
def analytics(request):
    """Analytics dashboard - Coming Soon"""
    return render(request, 'adminpanel/analytics.html')


