from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from products.models import Product
from .models import Wishlist
from .forms import CustomUserCreationForm
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import logout

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
                    messages.success(request, f'Welcome back, {user.username}!')
                    return redirect('adminpanel:dashboard')
                else:
                    messages.success(request, f'Welcome back, {user.username}!')
                    next_url = request.POST.get('next') or request.GET.get('next', 'home:index')
                    return redirect(next_url)
        else:
            messages.error(request, 'Invalid username or password.')
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
            messages.success(
                request,
                f"Welcome, {user.username}! Your account has been created successfully!",
            )
            return redirect("home:index")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = CustomUserCreationForm()

    context = {
        "form": form,
    }
    return render(request, "accounts/register.html", context)


@login_required
def profile(request):
    """User profile page"""
    if request.method == "POST":
        user = request.user
        user.first_name = request.POST.get("first_name", "")
        user.last_name = request.POST.get("last_name", "")
        user.email = request.POST.get("email", "")
        user.save()

        messages.success(request, "Profile updated successfully!")
        return redirect("accounts:profile")

    context = {
        "user": request.user,
    }
    return render(request, "accounts/profile.html", context)


@login_required
def wishlist(request):
    """User's wishlist"""
    wishlist_items = Wishlist.objects.filter(user=request.user).select_related(
        "product"
    )

    context = {
        "wishlist_items": wishlist_items,
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

        if created:
            messages.success(request, f"{product.name} added to wishlist!")
        else:
            messages.info(request, f"{product.name} is already in your wishlist")

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

        messages.success(request, f"{product.name} removed from wishlist")
        return redirect("accounts:wishlist")

    return redirect("accounts:wishlist")
