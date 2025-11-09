from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, get_user_model, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm
from products.models import Product
from .models import Wishlist, ChatConversation, ChatMessage
from .forms import CustomUserCreationForm, UserProfileForm, WelcomePersonalizationForm
from django.contrib.auth import logout
import json

User = get_user_model()


def user_login(request):
    """User login - redirects staff to admin dashboard"""
    if request.user.is_authenticated:
        # If already logged in, redirect based on user type
        if request.user.is_staff:
            return redirect('adminpanel:dashboard')
        return redirect('home:index')
    
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            
            if user is not None:
                login(request, user)
                
                # Check if user is staff and redirect accordingly
                if user.is_staff:
                    return redirect('adminpanel:dashboard')
                else:
                    next_url = request.POST.get('next') or request.GET.get('next', 'home:index')
                    return redirect(next_url)
        else:
            messages.error(request, 'Invalid credentials. Please try again.')
    else:
        form = AuthenticationForm()
    
    return render(request, 'accounts/login.html', {
        'form': form,
        'next': request.GET.get('next', '')
    })

def register(request):
    """User registration"""
    if request.user.is_authenticated:
        return redirect("home:index")

    if request.method == "POST":
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            # Redirect to welcome personalization screen without toast
            return redirect("accounts:welcome")
        else:
            # Don't show generic error message, let form errors show
            pass
    else:
        form = CustomUserCreationForm()

    context = {
        "form": form,
    }
    return render(request, "accounts/register.html", context)


@login_required
def welcome_personalization(request):
    """Welcome screen for new users to personalize their experience"""
    # # COMMENTED OUT: Preferred category is redundant - ML model should be primary
    # # If user already has shopping preference set, skip to home
    # if request.user.preferred_category:
    #     return redirect("home:index")
    
    if request.method == "POST":
        form = WelcomePersonalizationForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated! Enjoy your personalized experience.")
            return redirect("home:index")
    else:
        form = WelcomePersonalizationForm(instance=request.user)
    
    return render(request, "accounts/welcome.html", {"form": form})


@login_required
def profile(request):
    """User profile page with edit functionality"""
    # Get user statistics
    total_orders = 0
    wishlist_count = Wishlist.objects.filter(user=request.user).count()
    recent_orders = []
    
    try:
        from orders.models import Order
        total_orders = Order.objects.filter(user=request.user).count()
        recent_orders = Order.objects.filter(user=request.user).order_by('-created_at')[:5]
    except:
        pass

    # Handle AJAX form submission
    if request.method == "POST" and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        form = UserProfileForm(request.POST, instance=request.user, user=request.user)
        
        if form.is_valid():
            form.save()
            return JsonResponse({
                'success': True,
                'message': 'Profile updated successfully!',
                'user': {
                    'first_name': request.user.first_name,
                    'last_name': request.user.last_name,
                    'full_name': request.user.get_full_name(),
                    'email': request.user.email,
                    'phone': request.user.phone or '',
                    'date_of_birth': request.user.date_of_birth.strftime('%Y-%m-%d') if request.user.date_of_birth else '',
                }
            })
        else:
            # Return validation errors
            errors = {}
            for field, error_list in form.errors.items():
                errors[field] = [str(error) for error in error_list]
            
            return JsonResponse({
                'success': False,
                'message': 'Please correct the errors below.',
                'errors': errors
            }, status=400)

    # Handle regular form submission (fallback)
    if request.method == "POST":
        form = UserProfileForm(request.POST, instance=request.user, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully!")
            return redirect("accounts:profile")
        # Don't show generic error, let form errors display
    else:
        form = UserProfileForm(instance=request.user, user=request.user)

    context = {
        "user": request.user,
        "form": form,
        "total_orders": total_orders,
        "wishlist_count": wishlist_count,
        "recent_orders": recent_orders,
    }
    return render(request, "accounts/profile.html", context)


@login_required
def update_demographics(request):
    """Update user demographics for ML recommendations"""
    if request.method == "POST":
        user = request.user
        
        # Update demographic fields
        if request.POST.get('age_range'):
            user.age_range = request.POST.get('age_range')
        if request.POST.get('gender'):
            user.gender = request.POST.get('gender')
        if request.POST.get('household_size'):
            user.household_size = request.POST.get('household_size')
        if request.POST.get('has_children'):
            user.has_children = request.POST.get('has_children') == 'true'
        if request.POST.get('occupation'):
            user.occupation = request.POST.get('occupation')
        if request.POST.get('education'):
            user.education = request.POST.get('education')
        if request.POST.get('employment'):
            user.employment = request.POST.get('employment')
        if request.POST.get('income_range'):
            user.income_range = request.POST.get('income_range')
        
        user.save()
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': 'Profile updated successfully! Your recommendations will be more personalized.'
            })
        else:
            messages.success(request, 'Profile updated successfully!')
            return redirect('accounts:profile')
    
    return redirect('accounts:profile')


@login_required
def wishlist(request):
    """User's wishlist with detailed product information"""
    wishlist_items = Wishlist.objects.filter(user=request.user).select_related(
        "product_variant__product", "product"
    ).prefetch_related(
        "product__images",
        "product_variant__product__images"
    ).order_by('-added_at')

    # Enrich wishlist items with additional data
    for item in wishlist_items:
        # Determine the actual product (could be from product or product_variant)
        if item.product_variant:
            item.display_product = item.product_variant.product
            item.display_variant = item.product_variant
            item.display_price = item.product_variant.price
            item.in_stock = item.product_variant.stock > 0
            item.stock_count = item.product_variant.stock
        elif item.product:
            item.display_product = item.product
            # Get the lowest priced variant as default
            lowest_variant = item.product.variants.filter(stock__gt=0).order_by('price').first()
            item.display_variant = lowest_variant
            item.display_price = lowest_variant.price if lowest_variant else 0
            item.in_stock = lowest_variant is not None
            item.stock_count = lowest_variant.stock if lowest_variant else 0

    context = {
        "wishlist_items": wishlist_items,
        "wishlist_count": wishlist_items.count(),
    }
    return render(request, "accounts/wishlist.html", context)


@login_required
def add_to_wishlist(request, product_id):
    """Add product to wishlist"""
    if request.method == "POST":
        product = get_object_or_404(Product, id=product_id)
        wishlist_item, created = Wishlist.objects.get_or_create(
            user=request.user, product=product
        )

        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse(
                {
                    "success": True,
                    "message": (
                        "Added to wishlist" if created else "Already in wishlist"
                    ),
                }
            )

        # No toast for wishlist actions
        return redirect("products:product_detail", slug=product.slug)

    return redirect("products:product_list")


@login_required
def remove_from_wishlist(request, product_id):
    """Remove product from wishlist"""
    if request.method == "POST":
        product = get_object_or_404(Product, id=product_id)
        wishlist_item = get_object_or_404(Wishlist, user=request.user, product=product)
        wishlist_item.delete()

        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({"success": True, "message": "Removed from wishlist"})

        # No toast for wishlist removal
        return redirect("accounts:wishlist")

    return redirect("accounts:wishlist")


@login_required
def move_to_cart(request, wishlist_id):
    """Move item from wishlist to cart"""
    if request.method == "POST":
        from cart.models import Cart, CartItem
        from decimal import Decimal
        
        wishlist_item = get_object_or_404(Wishlist, id=wishlist_id, user=request.user)
        
        # Determine which variant to add
        if wishlist_item.product_variant:
            variant = wishlist_item.product_variant
            product = wishlist_item.product_variant.product
        elif wishlist_item.product:
            # Get lowest priced variant with stock
            product = wishlist_item.product
            variant = product.variants.filter(stock__gt=0).order_by('price').first()
            
            if not variant:
                if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                    return JsonResponse({
                        "success": False,
                        "message": f"{product.name} is currently out of stock"
                    })
                messages.error(request, f"{product.name} is currently out of stock")
                return redirect("accounts:wishlist")
        else:
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return JsonResponse({
                    "success": False,
                    "message": "Unable to move this item to cart"
                })
            messages.error(request, "Unable to move this item to cart")
            return redirect("accounts:wishlist")
        
        # Check stock availability (consolidated check)
        if variant.stock < 1:
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return JsonResponse({
                    "success": False,
                    "message": f"{product.name} is currently out of stock"
                })
            messages.error(request, f"{product.name} is currently out of stock")
            return redirect("accounts:wishlist")
        
        # Get or create cart
        cart, _ = Cart.objects.get_or_create(user=request.user)
        
        # Add to cart or update quantity
        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            product_variant=variant,
            defaults={'quantity': 1}
        )
        
        if not created:
            # Item already in cart, increase quantity
            if cart_item.quantity < variant.stock:
                cart_item.quantity += 1
                cart_item.save()
            else:
                if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                    return JsonResponse({
                        "success": False,
                        "message": f"Only {variant.stock} left in stock"
                    })
                # No toast for stock warning
                return redirect("accounts:wishlist")
        
        # Remove from wishlist
        wishlist_item.delete()
        
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({
                "success": True,
                "message": "Moved to cart"
            })
        
        # No toast for move to cart
        return redirect("accounts:wishlist")
    
    return redirect("accounts:wishlist")

@require_http_methods(["GET"])
@login_required
def list_conversations(request):
    """List all conversations for the authenticated user"""
    conversations = ChatConversation.objects.filter(
        user=request.user
    ).select_related('admin', 'product').order_by('-updated_at')
    
    data = []
    for conv in conversations:
        messages_data = []
        for msg in conv.messages.all().select_related('sender')[:50]:  # Last 50 messages
            messages_data.append({
                'id': msg.id,
                'content': msg.content,
                'sender': msg.sender.id,
                'created_at': msg.created_at.isoformat(),
            })
        
        data.append({
            'id': conv.id,
            'subject': conv.subject,
            'message_type': conv.message_type,
            'status': conv.status,
            'user_has_unread': conv.user_has_unread,
            'admin_has_unread': conv.admin_has_unread,
            'created_at': conv.created_at.isoformat(),
            'updated_at': conv.updated_at.isoformat(),
            'messages': messages_data,
        })
    
    return JsonResponse({'results': data})


@require_http_methods(["POST"])
@login_required
def create_conversation(request):
    """Create a new conversation"""
    try:
        data = json.loads(request.body)
        subject = data.get('subject', 'New Conversation')
        
        # Auto-assign to staff using round-robin
        from adminpanel.views import get_next_assigned_staff
        next_staff = get_next_assigned_staff()
        
        conversation = ChatConversation.objects.create(
            user=request.user,
            subject=subject,
            admin=next_staff,
        )
        
        return JsonResponse({
            'id': conversation.id,
            'subject': conversation.subject,
            'message_type': conversation.message_type,
            'status': conversation.status,
            'user_has_unread': conversation.user_has_unread,
            'admin_has_unread': conversation.admin_has_unread,
            'created_at': conversation.created_at.isoformat(),
            'updated_at': conversation.updated_at.isoformat(),
            'messages': [],
        }, status=201)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@require_http_methods(["GET"])
@login_required
def get_conversation(request, conversation_id):
    """Get a specific conversation with all messages"""
    conversation = get_object_or_404(
        ChatConversation.objects.select_related('admin', 'product'),
        id=conversation_id,
        user=request.user
    )
    
    messages_data = []
    for msg in conversation.messages.all().select_related('sender'):
        messages_data.append({
            'id': msg.id,
            'content': msg.content,
            'sender': msg.sender.id,
            'created_at': msg.created_at.isoformat(),
        })
    
    return JsonResponse({
        'id': conversation.id,
        'subject': conversation.subject,
        'message_type': conversation.message_type,
        'status': conversation.status,
        'user_has_unread': conversation.user_has_unread,
        'admin_has_unread': conversation.admin_has_unread,
        'created_at': conversation.created_at.isoformat(),
        'updated_at': conversation.updated_at.isoformat(),
        'messages': messages_data,
    })


@require_http_methods(["POST"])
@login_required
def send_message(request, conversation_id):
    """Send a message in a conversation"""
    conversation = get_object_or_404(
        ChatConversation,
        id=conversation_id,
        user=request.user
    )
    
    try:
        data = json.loads(request.body)
        content = data.get('content', '').strip()
        
        if not content:
            return JsonResponse({'error': 'Message content is required'}, status=400)
        
        message = ChatMessage.objects.create(
            conversation=conversation,
            sender=request.user,
            content=content
        )
        
        # Update conversation status
        conversation.status = 'pending'
        conversation.admin_has_unread = True
        conversation.save()
        
        return JsonResponse({
            'id': message.id,
            'content': message.content,
            'sender': message.sender.id,
            'created_at': message.created_at.isoformat(),
        }, status=201)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@require_http_methods(["POST"])
@login_required
def mark_conversation_read(request, conversation_id):
    """Mark conversation as read for the user"""
    conversation = get_object_or_404(
        ChatConversation,
        id=conversation_id,
        user=request.user
    )
    
    conversation.user_has_unread = False
    conversation.save()
    
    return JsonResponse({'success': True})


@require_http_methods(["DELETE"])
@login_required
def delete_conversation(request, conversation_id):
    """Delete a conversation"""
    conversation = get_object_or_404(
        ChatConversation,
        id=conversation_id,
        user=request.user
    )
    
    conversation.delete()
    
    return JsonResponse({'success': True}, status=204)


@require_http_methods(["GET"])
@login_required
def get_wishlist_count(request):
    """Get the count of wishlist items"""
    count = Wishlist.objects.filter(user=request.user).count()
    return JsonResponse({'count': count})
@require_http_methods(["POST"])
@login_required
def change_password(request):
    """Change user password"""
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        form = PasswordChangeForm(user=request.user, data=request.POST)
        
        if form.is_valid():
            user = form.save()
            # Update session to prevent logout
            update_session_auth_hash(request, user)
            return JsonResponse({
                'success': True,
                'message': 'Password changed successfully!'
            })
        else:
            # Return validation errors
            errors = {}
            for field, error_list in form.errors.items():
                errors[field] = [str(error) for error in error_list]
            
            return JsonResponse({
                'success': False,
                'message': 'Please correct the errors below.',
                'errors': errors
            }, status=400)
    
    # Fallback for non-AJAX requests
    if request.method == "POST":
        form = PasswordChangeForm(user=request.user, data=request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Password changed successfully!')
            return redirect('accounts:profile')
        else:
            messages.error(request, 'Please correct the errors below.')
    
    return redirect('accounts:profile')

# # COMMENTED OUT: Preferred category is redundant - ML model should be primary
# @require_http_methods(["POST"])
# @login_required
# def update_shopping_interest(request):
#     """Update user's shopping interest/preferred category"""
#     try:
#         shopping_interest = request.POST.get('shopping_interest', '').strip()
#         
#         if not shopping_interest:
#             return JsonResponse({
#                 'success': False,
#                 'message': 'Please select a shopping interest'
#             }, status=400)
#         
#         # Map shopping interest to category name
#         # This maps the form values to actual category names in the database
#         category_mapping = {
#             'Electronics': 'Electronics',
#             'Fashion - Men': 'Men\'s Fashion',
#             'Fashion - Women': 'Women\'s Fashion',
#             'Home & Kitchen': 'Home & Kitchen',
#             'Beauty & Personal Care': 'Beauty & Personal Care',
#             'Sports & Outdoors': 'Sports & Outdoors',
#             'Books': 'Books',
#             'Groceries & Gourmet': 'Groceries & Gourmet',
#             'Pet Supplies': 'Pet Supplies',
#             'Automotive': 'Automotive',
#         }
#         
#         # Get the mapped category name, or use the original if not in mapping
#         category_name = category_mapping.get(shopping_interest, shopping_interest)
#         
#         # Map shopping interest to category
#         from products.models import Category
#         try:
#             # Try exact match first
#             category = Category.objects.filter(name=category_name, is_active=True).first()
#             
#             # If not found, try case-insensitive match
#             if not category:
#                 category = Category.objects.filter(
#                     name__iexact=category_name, 
#                     is_active=True
#                 ).first()
#             
#             # If still not found, try partial match
#             if not category:
#                 category = Category.objects.filter(
#                     name__icontains=category_name.split()[0] if category_name.split() else category_name,
#                     is_active=True
#                 ).first()
#             
#             if not category:
#                 # Return all available categories for debugging
#                 available_categories = list(Category.objects.filter(is_active=True).values_list('name', flat=True))
#                 return JsonResponse({
#                     'success': False,
#                     'message': f'Category "{category_name}" not found. Available categories: {", ".join(available_categories[:10])}'
#                 }, status=400)
#             
#             request.user.preferred_category = category
#             request.user.save()
#             
#             return JsonResponse({
#                 'success': True,
#                 'message': f'Shopping interest updated to {category.name}!',
#                 'category_name': category.name,
#                 'category_id': category.id
#             })
#         except Exception as e:
#             return JsonResponse({
#                 'success': False,
#                 'message': f'Error updating category: {str(e)}'
#             }, status=500)
#     except Exception as e:
#         return JsonResponse({
#             'success': False,
#             'message': str(e)
#         }, status=500)




