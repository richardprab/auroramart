from django.shortcuts import render
from django.db.models import Q, Case, When, IntegerField
from products.models import Product, Category


def index(request):
    """Home page view"""
    # Featured products for "Recommended For You" section
    featured_products = (
        Product.objects.filter(is_active=True, is_featured=True)
        .select_related("category")
        .prefetch_related("images", "variants")[:8]
    )

    # Get all parent categories (categories without parent)
    cats = list(
        Category.objects.filter(parent__isnull=True, is_active=True)
        .only("id", "name", "slug")
        .order_by("name")
    )

    # Attach accurate product_count (includes direct children)
    for c in cats:
        cat_ids = Category.objects.filter(Q(id=c.id) | Q(parent_id=c.id)).values_list(
            "id", flat=True
        )
        c.product_count = (
            Product.objects.filter(is_active=True, category_id__in=cat_ids)
            .distinct()
            .count()
        )
    
    # Get user's wishlist items if authenticated
    user_wishlist_ids = []
    if request.user.is_authenticated:
        from accounts.models import Wishlist
        user_wishlist_ids = list(
            Wishlist.objects.filter(user=request.user)
            .values_list('product_id', flat=True)
        )

    return render(
        request,
        "home/index.html",
        {
            "categories": cats,
            "featured_products": featured_products,
            "user_wishlist_ids": user_wishlist_ids,
        },
    )

    return render(
        request,
        "home/index.html",
        {
            "featured_products": featured_products,
            "categories": cats,
            "user_wishlist_ids": user_wishlist_ids,
        },
    )


def about(request):
    """About page view"""
    return render(request, "home/about.html")


def contact(request):
    """Contact page view"""
    return render(request, "home/contact.html")
