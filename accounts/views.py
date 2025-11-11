from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, get_user_model, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm
from django.core.paginator import Paginator
from products.models import Product
from .models import Wishlist, Customer
from .forms import CustomUserCreationForm, UserProfileForm
from django.contrib.auth import logout
from decimal import Decimal
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
            # Get cleaned data
            username = form.cleaned_data['username']
            email = form.cleaned_data['email'].lower()
            password = form.cleaned_data['password1']
            first_name = form.cleaned_data['first_name'].strip()
            last_name = form.cleaned_data['last_name'].strip()
            
            # Create Customer directly (Customer extends User via multi-table inheritance)
            # This automatically creates both User and Customer records
            user = Customer.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
            )
            login(request, user)
            # Redirect to home after registration
            return redirect("home:index")
        else:
            pass
    else:
        form = CustomUserCreationForm()

    context = {
        "form": form,
    }
    return render(request, "accounts/register.html", context)


@login_required
def profile(request):
    """User profile page with edit functionality"""
    # Get user statistics
    total_orders = 0
    wishlist_count = Wishlist.objects.filter(user=request.user).count()
    recent_orders = []
    viewing_history = []
    
    try:
        from orders.models import Order
        total_orders = Order.objects.filter(user=request.user).count()
        recent_orders = Order.objects.filter(user=request.user).order_by('-created_at')[:5]
    except:
        pass
    
    # Get viewing history with pagination (10 per page)
    viewing_history_list = []
    viewing_history_page = None
    try:
        from .models import BrowsingHistory
        viewing_history_list = BrowsingHistory.objects.filter(
            user=request.user
        ).select_related('product').prefetch_related('product__images').order_by('-viewed_at')
        
        # Paginate viewing history (8 items per page)
        paginator = Paginator(viewing_history_list, 8)
        page_number = request.GET.get('page', 1)
        viewing_history_page = paginator.get_page(page_number)
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
        "viewing_history_page": viewing_history_page,
    }
    return render(request, "accounts/profile.html", context)


@login_required
def update_demographics(request):
    """Update user demographics for ML recommendations"""
    if request.method == "POST":
        user = request.user
        
        # Get Customer profile
        # With multi-table inheritance, check if user is a Customer instance
        # or if there's a Customer record with the same ID
        if isinstance(user, Customer):
            customer = user
        else:
            # Try to get the Customer instance
            try:
                customer = Customer.objects.get(id=user.id)
            except Customer.DoesNotExist:
                # User doesn't have Customer profile - this shouldn't happen for regular users
                # but could happen for staff/superusers
                return JsonResponse({
                    'success': False,
                    'message': 'Customer profile not found. Please contact support.'
                }, status=400)
        
        # Update demographic fields
        if request.POST.get('age'):
            customer.age = int(request.POST.get('age'))
        if request.POST.get('gender'):
            customer.gender = request.POST.get('gender')
        if request.POST.get('employment_status'):
            customer.employment_status = request.POST.get('employment_status')
        if request.POST.get('occupation'):
            customer.occupation = request.POST.get('occupation')
        if request.POST.get('education'):
            customer.education = request.POST.get('education')
        if request.POST.get('household_size'):
            customer.household_size = int(request.POST.get('household_size'))
        if request.POST.get('has_children') is not None:
            customer.has_children = request.POST.get('has_children') == 'true'
        if request.POST.get('monthly_income_sgd'):
            customer.monthly_income_sgd = Decimal(request.POST.get('monthly_income_sgd'))
        
        customer.save()
        
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
        return redirect("products:product_detail", sku=product.sku)

    return redirect("products:product_list")


@login_required
def remove_from_wishlist(request, product_id):
    """Remove product from wishlist"""
    if request.method == "POST":
        product = get_object_or_404(Product, id=product_id)
        try:
            wishlist_item = Wishlist.objects.get(user=request.user, product=product)
        except Wishlist.DoesNotExist:
            wishlist_item = Wishlist.objects.filter(
                user=request.user, 
                product_variant__product=product
            ).first()
            if not wishlist_item:
                if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                    return JsonResponse({"success": False, "message": "Item not in wishlist"}, status=404)
                return redirect("accounts:wishlist")
        
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


