from django.shortcuts import render, get_object_or_404
from django.db.models import Q, Min, Max, Prefetch
from django.core.paginator import Paginator
from .models import Product, Category, ProductVariant, ProductImage


def product_list(request):
    """List all products"""
    products = (
        Product.objects.filter(is_active=True)
        .prefetch_related(
            Prefetch(
                "variants", queryset=ProductVariant.objects.filter(is_active=True)
            ),
            Prefetch("images", queryset=ProductImage.objects.order_by("order")),
        )
        .annotate(min_price=Min("variants__price"), max_price=Max("variants__price"))
    )

    categories = Category.objects.all()

    # Filter by category
    category_slug = request.GET.get("category")
    if category_slug:
        category = get_object_or_404(Category, slug=category_slug)
        products = products.filter(category=category)

    # Sort products
    sort_by = request.GET.get("sort", "name")
    if sort_by == "price-low":
        products = products.order_by("min_price")
    elif sort_by == "price-high":
        products = products.order_by("-max_price")
    elif sort_by == "name":
        products = products.order_by("name")

    # Pagination
    paginator = Paginator(products, 12)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "page_obj": page_obj,
        "categories": categories,
    }
    return render(request, "products/product_list.html", context)


def product_detail(request, slug):
    """Product detail page"""
    product = get_object_or_404(
        Product.objects.prefetch_related(
            Prefetch(
                "variants", queryset=ProductVariant.objects.filter(is_active=True)
            ),
            Prefetch("images", queryset=ProductImage.objects.order_by("order")),
        ),
        slug=slug,
        is_active=True,
    )

    related_products = (
        Product.objects.filter(category=product.category, is_active=True)
        .exclude(id=product.id)
        .prefetch_related(
            Prefetch(
                "variants", queryset=ProductVariant.objects.filter(is_active=True)
            ),
            Prefetch("images", queryset=ProductImage.objects.order_by("order")),
        )[:4]
    )

    context = {
        "product": product,
        "related_products": related_products,
    }
    return render(request, "products/product_detail.html", context)


def category_list(request, slug):
    """List products by category"""
    category = get_object_or_404(Category, slug=slug)
    products = Product.objects.filter(
        category=category, is_active=True
    ).prefetch_related(
        Prefetch("variants", queryset=ProductVariant.objects.filter(is_active=True)),
        Prefetch("images", queryset=ProductImage.objects.order_by("order")),
    )

    context = {
        "category": category,
        "products": products,
    }
    return render(request, "products/category_list.html", context)


def search(request):
    """Search products"""
    query = request.GET.get("q", "")
    products = Product.objects.filter(is_active=True).prefetch_related(
        Prefetch("variants", queryset=ProductVariant.objects.filter(is_active=True)),
        Prefetch("images", queryset=ProductImage.objects.order_by("order")),
    )

    if query:
        products = products.filter(
            Q(name__icontains=query)
            | Q(description__icontains=query)
            | Q(category__name__icontains=query)
        )

    context = {
        "products": products,
        "query": query,
    }
    return render(request, "products/search.html", context)
