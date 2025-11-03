from django.shortcuts import render
from django.db.models import Q, Case, When, IntegerField
from products.models import Product, Category


def index(request):
    """Home page view"""
    featured_products = (
        Product.objects.filter(is_active=True)
        .select_related("category")
        .prefetch_related("images", "variants")[:8]
    )

    # Keep placeholders order from the seed: Electronics, Fashion, Home & Garden, Sports
    slugs = ["electronics", "fashion", "home-garden", "sports"]
    ordering = Case(
        *[When(slug=s, then=idx) for idx, s in enumerate(slugs)],
        default=len(slugs),
        output_field=IntegerField(),
    )

    cats = list(
        Category.objects.filter(slug__in=slugs, is_active=True)
        .only("id", "name", "slug", "parent")
        .order_by(ordering)
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

    return render(
        request,
        "home/index.html",
        {
            "featured_products": featured_products,
            "categories": cats,
        },
    )


def about(request):
    """About page view"""
    return render(request, "home/about.html")


def contact(request):
    """Contact page view"""
    return render(request, "home/contact.html")
