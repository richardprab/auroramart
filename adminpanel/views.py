from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.db.models import Q, Count, Sum
from django.utils import timezone
from django.core.files.base import ContentFile
from datetime import timedelta
import base64
import requests

from products.models import Product, ProductVariant, ProductImage, Category
from accounts.models import ChatConversation, ChatMessage, User
from orders.models import Order, OrderItem

# ==================== HELPER FUNCTIONS ====================

def get_next_assigned_staff():
    """
    Round-robin assignment of staff members.
    Returns the next staff member to be assigned based on ascending staff number.
    """
    # Get all staff users ordered by username (staff001, staff002, etc.)
    staff_users = User.objects.filter(is_staff=True, is_active=True).order_by('username')
    
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
    return render(request, 'adminpanel/products.html')

@staff_member_required
def search_product(request):
    """AJAX endpoint to search for products"""
    query = request.GET.get('query', '')
    
    if not query:
        return JsonResponse({'error': 'No search query provided'}, status=400)
    
    # Search by slug, name, or SKU
    products = Product.objects.filter(
        Q(slug__icontains=query) | 

        Q(variants__sku__icontains=query)
    ).distinct().prefetch_related('variants__main_image', 'images', 'category')[:10]  # FIXED: Use main_image
    
    results = []
    for product in products:
        # Get product images
        product_images = []
        for img in product.images.all():
            product_images.append({
                'id': img.id,
                'url': img.image.url if img.image else '',
                'is_primary': img.is_primary,
            })
        
        # Get variants
        variants = []
        for variant in product.variants.all():
            variant_images = []
            # Variants use main_image (single ForeignKey to ProductImage)
            if variant.main_image:
                variant_images.append({
                    'id': variant.main_image.id,
                    'url': variant.main_image.image.url if variant.main_image.image else '',
                })
            
            variants.append({
                'id': variant.id,
                'sku': variant.sku,
                'name': variant.sku,  # Variants don't have 'name', use SKU or product name
                'stock': variant.stock,
                'price': str(variant.price),
                'images': variant_images,
            })
        
        results.append({
            'id': product.id,
            'name': product.name,
            'slug': product.slug,
            'description': product.description,
            'category': product.category.name if product.category else '',
            'category_id': product.category.id if product.category else None,
            'images': product_images,
            'variants': variants,
        })
    
    return JsonResponse({'products': results})

@staff_member_required
def update_product(request):
    """Update product details"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request method'}, status=400)
    
    try:
        product_id = request.POST.get('product_id')
        product = get_object_or_404(Product, id=product_id)
        
        # Update basic product info
        product.name = request.POST.get('name', product.name)
        product.description = request.POST.get('description', product.description)
        
        # Update category if provided
        category_name = request.POST.get('category')
        if category_name:
            category, created = Category.objects.get_or_create(name=category_name)
            product.category = category
        
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
        elif product_image_url and product_image_url.startswith('http'):  # ADDED: Check if URL starts with http
            # URL provided - download and save
            from django.core.files.base import ContentFile
            import requests
            
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
                variant_name = request.POST.get(f'variant_name_{index}')
                variant_stock = request.POST.get(f'variant_stock_{index}')
                variant_price = request.POST.get(f'variant_price_{index}')
                
                if variant_stock:
                    variant.stock = int(variant_stock)
                if variant_price:
                    variant.price = float(variant_price)
                
                variant.save()
                
                # Handle variant image
                variant_image_url = request.POST.get(f'variant_image_url_{index}', '').strip()
                variant_image_file = request.FILES.get(f'variant_image_file_{index}')
                
                if variant_image_file:
                    # File upload takes priority
                    if variant.main_image:
                        variant.main_image.image = variant_image_file
                        variant.main_image.save()
                    else:
                        new_image = ProductImage.objects.create(
                            product=product,
                            image=variant_image_file,
                            is_primary=False
                        )
                        variant.main_image = new_image
                        variant.save()
                        
                elif variant_image_url and variant_image_url.startswith('http'):  # ADDED: Check if URL starts with http
                    # URL provided - download and save
                    from django.core.files.base import ContentFile
                    import requests
                    
                    try:
                        response = requests.get(variant_image_url, timeout=10)
                        if response.status_code == 200:
                            file_name = variant_image_url.split('/')[-1]
                            if variant.main_image:
                                variant.main_image.image.save(file_name, ContentFile(response.content), save=True)
                            else:
                                new_image = ProductImage.objects.create(product=product, is_primary=False)
                                new_image.image.save(file_name, ContentFile(response.content), save=True)
                                variant.main_image = new_image
                                variant.save()
                    except Exception as e:
                        print(f"Error downloading variant image: {e}")
                        
            except ProductVariant.DoesNotExist:
                continue
            except Exception as e:
                print(f"Error updating variant {variant_id}: {e}")
                continue
        
        return JsonResponse({'success': True, 'message': 'Product updated successfully'})
        
    except Exception as e:
        print(f"Error in update_product: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': str(e)}, status=500)

# ==================== ORDER MANAGEMENT ====================

@staff_member_required
def order_management(request):
    """Order search and management page"""
    
    search_query = request.GET.get('search', '').strip()
    order_data = None
    customer_orders = None
    search_type = None
    
    if search_query:
        # Try to determine if it's an order number or customer username
        if search_query.upper().startswith('ORD'):
            # Search for specific order by order_number
            try:
                # Search by order_number field (e.g., ORD-A1B2C3D4)
                order = Order.objects.select_related('user', 'address').prefetch_related('items__variant__product').get(order_number__iexact=search_query)
                order_data = order
                search_type = 'order'
            except Order.DoesNotExist:
                pass
        
        else:
            # Try searching by order_number (without ORD prefix) or username
            try:
                # Try as order number (with or without ORD prefix)
                order = Order.objects.select_related('user', 'address').prefetch_related('items__variant__product').get(
                    Q(order_number__iexact=search_query) | 
                    Q(order_number__iexact=f'ORD-{search_query}')
                )
                order_data = order
                search_type = 'order'
            except Order.DoesNotExist:
                # Try as username
                try:
                    customer = User.objects.get(username__iexact=search_query)
                    customer_orders = Order.objects.filter(user=customer).select_related('user').order_by('-created_at')
                    search_type = 'customer'
                except User.DoesNotExist:
                    pass
    
    # Get all available variants for order editing
    all_variants = ProductVariant.objects.filter(stock__gt=0).select_related('product')
    
    context = {
        'search_query': search_query,
        'order': order_data,
        'customer_orders': customer_orders,
        'search_type': search_type,
        'all_variants': all_variants,
        'location_choices': Order.LOCATION_CHOICES,
        'status_choices': Order.STATUS_CHOICES,
    }
    
    return render(request, 'adminpanel/order_management.html', context)

@staff_member_required
def update_order(request, order_id):
    """Update order details via AJAX"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request method'}, status=400)
    
    try:
        order = get_object_or_404(Order, id=order_id)
        
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
        
        return JsonResponse({'success': True, 'message': 'Order updated successfully'})
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

# ==================== ANALYTICS ====================

@staff_member_required
def analytics(request):
    """Analytics dashboard - Coming Soon"""
    return render(request, 'adminpanel/analytics.html')


