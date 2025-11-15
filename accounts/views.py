from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, get_user_model, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm
from django.core.paginator import Paginator
from django.db.models import Q
from products.models import Product
from .models import Wishlist, Address, Customer
from .forms import CustomUserCreationForm, UserProfileForm, AddressForm
from decimal import Decimal

User = get_user_model()


def user_login(request):
    """
    User login - only allows Customer login via username or email.
    Staff users are explicitly rejected with a clear error message.
    """
    # If user is already authenticated, check if they're a Customer
    if request.user.is_authenticated:
        if isinstance(request.user, Customer):
            return redirect('home:index')
        else:
            # Staff/Superuser logged in - log them out and show error
            from django.contrib.auth import logout
            logout(request)
            messages.error(request, 'Staff accounts cannot access customer login. Please use the staff login page.')
    
    from django.contrib.auth.forms import AuthenticationForm
    form = AuthenticationForm()
    
    if request.method == 'POST':
        username_or_email = request.POST.get('username')
        password = request.POST.get('password')
        
        # First, check if this username/email belongs to a Staff user
        # If so, reject immediately with a clear message
        from .models import Staff
        try:
            staff_user = Staff.objects.filter(
                Q(username=username_or_email) | Q(email__iexact=username_or_email)
            ).first()
            if staff_user and staff_user.check_password(password):
                messages.error(
                    request, 
                    'Staff accounts cannot login here. Please use the staff login page at /adminpanel/login/'
                )
                return render(request, 'accounts/login.html', {
                    'form': form,
                    'next': request.GET.get('next', '')
                })
        except Exception:
            pass  # Continue with normal authentication
        
        # Use Django's authenticate() - this will use our custom backend
        # which only checks the Customer table (staff/superuser will return None)
        user = authenticate(request, username=username_or_email, password=password)
        
        if user is not None:
            # Double-check that the authenticated user is a Customer instance
            if not isinstance(user, Customer):
                messages.error(request, 'Invalid account type. Only customer accounts can login here.')
                return render(request, 'accounts/login.html', {
                    'form': form,
                    'next': request.GET.get('next', '')
                })
            
            login(request, user)
            next_url = request.POST.get('next') or request.GET.get('next', 'home:index')
            return redirect(next_url)
        else:
            # Authentication failed - show error message
            messages.error(request, 'Invalid credentials. Please try again.')
    
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
            # Specify backend for login since multiple backends are configured
            login(request, user, backend='accounts.backends.MultiUserModelBackend')
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
    voucher_count = 0
    
    try:
        from orders.models import Order
        total_orders = Order.objects.filter(user=request.user).count()
        recent_orders = Order.objects.filter(user=request.user).order_by('-created_at')[:5]
    except Exception:
        pass
    
    try:
        from vouchers.models import Voucher, VoucherUsage
        from django.utils import timezone
        now = timezone.now()
        # Count only available vouchers (user-specific + public that can actually be used)
        all_vouchers = Voucher.objects.filter(
            Q(user=request.user) | Q(user__isnull=True),
            is_active=True,
            start_date__lte=now,
            end_date__gte=now
        ).distinct()
        
        # Filter to only count vouchers that are actually available (not fully used, valid, and can be used)
        available_count = 0
        for voucher in all_vouchers:
            if not voucher.is_valid():
                continue
            
            usage_count = VoucherUsage.objects.filter(
                voucher=voucher,
                user=request.user
            ).count()
            
            if usage_count >= voucher.max_uses_per_user:
                continue
            
            if voucher.can_be_used_by_user(request.user, usage_count=usage_count):
                available_count += 1
        
        voucher_count = available_count
    except Exception:
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
    except Exception:
        pass

    # Handle AJAX form submission
    if request.method == "POST" and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        form = UserProfileForm(request.POST, instance=request.user, user=request.user)
        
        if form.is_valid():
            form.save()
            # Get phone from Customer if user is a Customer
            # Since AUTH_USER_MODEL is Customer, request.user is usually a Customer instance
            phone = ''
            if isinstance(request.user, Customer):
                phone = request.user.phone or ''
            else:
                # Edge case: staff/superuser - try to get phone if available
                try:
                    customer = Customer.objects.get(id=request.user.id)
                    phone = customer.phone or ''
                except Customer.DoesNotExist:
                    pass
            
            return JsonResponse({
                'success': True,
                'message': 'Profile updated successfully!',
                'user': {
                    'first_name': request.user.first_name,
                    'last_name': request.user.last_name,
                    'full_name': request.user.get_full_name(),
                    'email': request.user.email,
                    'phone': phone,
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
        "voucher_count": voucher_count,
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
        # Since AUTH_USER_MODEL is Customer, request.user is usually a Customer instance
        if isinstance(user, Customer):
            customer = user
        else:
            # Edge case: staff/superuser trying to update demographics
            try:
                customer = Customer.objects.get(id=user.id)
            except Customer.DoesNotExist:
                # User doesn't have Customer profile - staff/superusers can't update demographics
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
        
        # Check profile completion before saving
        was_complete = customer.get_profile_completion_percentage() == 100
        
        customer.save()
        
        # Check if profile is now complete and wasn't before
        is_now_complete = customer.get_profile_completion_percentage() == 100
        profile_just_completed = is_now_complete and not was_complete
        
        # Give profile completion voucher if profile was just completed
        if profile_just_completed:
            from vouchers.models import Voucher, VoucherUsage
            from accounts.models import Superuser
            from django.utils import timezone
            from datetime import timedelta
            from decimal import Decimal
            
            # Check if user already has the WELCOME voucher or has used it
            welcome_voucher = Voucher.objects.filter(promo_code='WELCOME', is_active=True).first()
            
            if welcome_voucher:
                # Check if user has already used this voucher
                usage_count = VoucherUsage.objects.filter(
                    voucher=welcome_voucher,
                    user=customer
                ).count()
                
                if usage_count == 0:
                    # User hasn't used it yet, they can use the existing public voucher
                    pass  # Voucher already exists and is available
                else:
                    # User already used it, no need to do anything
                    pass
            else:
                # Create the WELCOME voucher if it doesn't exist (should exist from populate_db, but just in case)
                superuser = Superuser.objects.filter(is_superuser=True).first()
                try:
                    Voucher.objects.create(
                        name='Welcome Discount',
                        promo_code='WELCOME',
                        description='Congratulations on completing your profile! You\'ve earned a 5% discount voucher as a reward. Use code WELCOME at checkout to apply this discount to your order.',
                        discount_type='percent',
                        discount_value=Decimal('5.00'),
                        max_discount=Decimal('50.00'),
                        min_purchase=Decimal('10.00'),
                        first_time_only=False,
                        max_uses=None,
                        max_uses_per_user=1,
                        start_date=timezone.now(),
                        end_date=timezone.now() + timedelta(days=365),
                        is_active=True,
                        user=None,  # Public voucher
                        created_by=superuser,
                    )
                except Exception:
                    pass  # Voucher might already exist, ignore error
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            message = 'Profile updated successfully! Your recommendations will be more personalized.'
            if profile_just_completed:
                message = 'Profile complete! You\'ve earned a 5% discount voucher (code: WELCOME)!'
            return JsonResponse({
                'success': True,
                'message': message,
                'profile_completed': profile_just_completed
            })
        else:
            if profile_just_completed:
                messages.success(request, 'Profile complete! You\'ve earned a 5% discount voucher (code: WELCOME)!')
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
            item.display_price = item.product_variant.effective_price
            item.in_stock = item.product_variant.stock > 0
            item.stock_count = item.product_variant.stock
        elif item.product:
            item.display_product = item.product
            # Get the lowest priced variant as default (order by base price, but use effective_price for display)
            lowest_variant = item.product.variants.filter(stock__gt=0).order_by('price').first()
            item.display_variant = lowest_variant
            item.display_price = lowest_variant.effective_price if lowest_variant else 0
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


@login_required
def addresses(request):
    """List user addresses"""
    addresses_list = Address.objects.filter(user=request.user, address_type='shipping').order_by('-is_default', '-created_at')
    
    # Return JSON for AJAX requests
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        addresses_data = [{
            'id': addr.id,
            'address_line1': addr.address_line1,
            'address_line2': addr.address_line2 or '',
            'city': addr.city,
            'state': addr.state,
            'postal_code': addr.postal_code,
            'country': addr.country,
            'is_default': addr.is_default,
        } for addr in addresses_list]
        
        return JsonResponse({
            'addresses': addresses_data,
            'address_count': addresses_list.count(),
        })
    
    context = {
        'addresses': addresses_list,
        'address_count': addresses_list.count(),
    }
    return render(request, 'accounts/addresses.html', context)


@require_http_methods(["GET", "POST"])
@login_required
def add_address(request):
    """Add a new address (max 3 addresses)"""
    # Check address limit
    address_count = Address.objects.filter(user=request.user, address_type='shipping').count()
    if address_count >= 3:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'message': 'You can only save up to 3 addresses. Please delete an existing address first.'
            }, status=400)
        messages.error(request, 'You can only save up to 3 addresses. Please delete an existing address first.')
        return redirect('accounts:addresses')
    
    if request.method == 'POST':
        form = AddressForm(request.POST, user=request.user)
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            if form.is_valid():
                address = form.save()
                return JsonResponse({
                    'success': True,
                    'message': 'Address added successfully!',
                    'address': {
                        'id': address.id,
                        'address_line1': address.address_line1,
                        'address_line2': address.address_line2 or '',
                        'city': address.city,
                        'state': address.state,
                        'postal_code': address.postal_code,
                        'country': address.country,
                        'is_default': address.is_default,
                    }
                })
            else:
                errors = {}
                for field, error_list in form.errors.items():
                    errors[field] = [str(error) for error in error_list]
                return JsonResponse({
                    'success': False,
                    'message': 'Please correct the errors below.',
                    'errors': errors
                }, status=400)
        else:
            if form.is_valid():
                form.save()
                messages.success(request, 'Address added successfully!')
                return redirect('accounts:addresses')
    else:
        form = AddressForm(user=request.user)
    
    return render(request, 'accounts/add_address.html', {'form': form})


@require_http_methods(["GET", "POST"])
@login_required
def edit_address(request, address_id):
    """Edit an existing address"""
    address = get_object_or_404(Address, id=address_id, user=request.user)
    
    if request.method == 'POST':
        form = AddressForm(request.POST, instance=address, user=request.user)
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            if form.is_valid():
                address = form.save()
                return JsonResponse({
                    'success': True,
                    'message': 'Address updated successfully!',
                    'address': {
                        'id': address.id,
                        'address_line1': address.address_line1,
                        'address_line2': address.address_line2 or '',
                        'city': address.city,
                        'state': address.state,
                        'postal_code': address.postal_code,
                        'country': address.country,
                        'is_default': address.is_default,
                    }
                })
            else:
                errors = {}
                for field, error_list in form.errors.items():
                    errors[field] = [str(error) for error in error_list]
                return JsonResponse({
                    'success': False,
                    'message': 'Please correct the errors below.',
                    'errors': errors
                }, status=400)
        else:
            if form.is_valid():
                form.save()
                messages.success(request, 'Address updated successfully!')
                return redirect('accounts:addresses')
    else:
        form = AddressForm(instance=address, user=request.user)
    
    return render(request, 'accounts/edit_address.html', {'form': form, 'address': address})


@require_http_methods(["POST"])
@login_required
def delete_address(request, address_id):
    """Delete an address"""
    address = get_object_or_404(Address, id=address_id, user=request.user)
    
    if request.method == 'POST':
        address.delete()
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': 'Address deleted successfully!'
            })
        
        messages.success(request, 'Address deleted successfully!')
        return redirect('accounts:addresses')
    
    return redirect('accounts:addresses')


@require_http_methods(["POST"])
@login_required
def set_default_address(request, address_id):
    """Set an address as default"""
    address = get_object_or_404(Address, id=address_id, user=request.user)
    
    if request.method == 'POST':
        address.is_default = True
        address.save()  # This will automatically unset other defaults via the model's save method
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': 'Default address updated successfully!'
            })
        
        messages.success(request, 'Default address updated successfully!')
        return redirect('accounts:addresses')
    
    return redirect('accounts:addresses')

