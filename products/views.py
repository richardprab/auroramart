from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator
from django.db.models import Q, Min, Max, Count
from decimal import Decimal
from .models import Product, Category, ProductVariant


def product_list(request):
    """Display list of products with advanced filtering"""
    products = (
        Product.objects.filter(is_active=True)
        .select_related("category")
        .prefetch_related("images", "variants")
    )

    # Category filter
    category_slug = request.GET.get("category")
    selected_category = None
    if category_slug:
        try:
            selected_category = Category.objects.get(slug=category_slug, is_active=True)
            # Get all descendant categories (including self)
            category_ids = [selected_category.id]
            if selected_category.parent is None:
                child_categories = Category.objects.filter(parent=selected_category)
                category_ids.extend(child_categories.values_list("id", flat=True))
            products = products.filter(category_id__in=category_ids)
        except Category.DoesNotExist:
            pass

    # Search query
    query = request.GET.get("q", "")
    if query:
        products = products.filter(
            Q(name__icontains=query)
            | Q(description__icontains=query)
            | Q(category__name__icontains=query)
            | Q(brand__icontains=query)
        )

    # Price range filter
    min_price = request.GET.get("min_price")
    max_price = request.GET.get("max_price")
    if min_price:
        try:
            products = products.filter(variants__price__gte=Decimal(min_price))
        except:
            pass
    if max_price:
        try:
            products = products.filter(variants__price__lte=Decimal(max_price))
        except:
            pass

    # Brand filter
    brands = request.GET.getlist("brand")
    if brands:
        products = products.filter(brand__in=brands)

    # Color filter
    colors = request.GET.getlist("color")
    if colors:
        products = products.filter(variants__color__in=colors)

    # Size filter
    sizes = request.GET.getlist("size")
    if sizes:
        products = products.filter(variants__size__in=sizes)

    # Remove duplicates after filtering
    products = products.distinct()

    # Sort
    sort_by = request.GET.get("sort", "featured")
    if sort_by == "price_low":
        products = products.annotate(min_price=Min("variants__price")).order_by(
            "min_price"
        )
    elif sort_by == "price_high":
        products = products.annotate(max_price=Max("variants__price")).order_by(
            "-max_price"
        )
    elif sort_by == "newest":
        products = products.order_by("-created_at")
    elif sort_by == "name":
        products = products.order_by("name")
    else:  # featured
        products = products.order_by("-is_featured", "-is_bestseller", "-created_at")

    # Get filter options (available brands, colors, sizes)
    if selected_category:
        filter_products = Product.objects.filter(
            is_active=True, category_id__in=category_ids
        )
    else:
        filter_products = Product.objects.filter(is_active=True)

    available_brands = (
        filter_products.exclude(brand="")
        .values_list("brand", flat=True)
        .distinct()
        .order_by("brand")
    )
    available_colors = (
        ProductVariant.objects.filter(product__in=filter_products, color__isnull=False)
        .exclude(color="")
        .values_list("color", flat=True)
        .distinct()
        .order_by("color")
    )
    available_sizes = (
        ProductVariant.objects.filter(product__in=filter_products, size__isnull=False)
        .exclude(size="")
        .values_list("size", flat=True)
        .distinct()
        .order_by("size")
    )

    # Get price range
    price_range = filter_products.aggregate(
        min_price=Min("variants__price"), max_price=Max("variants__price")
    )

    # Pagination
    paginator = Paginator(products, 12)
    page_number = request.GET.get("page", 1)
    page_obj = paginator.get_page(page_number)

    # Get all categories for sidebar
    categories = Category.objects.filter(
        parent__isnull=True, is_active=True
    ).prefetch_related("children")

    # Build query string for pagination
    query_params = request.GET.copy()
    if "page" in query_params:
        query_params.pop("page")
    query_string = query_params.urlencode()

    context = {
        "page_obj": page_obj,
        "categories": categories,
        "selected_category": selected_category,
        "query": query,
        "sort_by": sort_by,
        "query_string": query_string,
        # Filter options
        "available_brands": available_brands,
        "available_colors": available_colors,
        "available_sizes": available_sizes,
        "selected_brands": brands,
        "selected_colors": colors,
        "selected_sizes": sizes,
        "min_price": min_price or "",
        "max_price": max_price or "",
        "price_range": price_range,
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
