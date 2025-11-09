from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator
from django.db.models import Q, Min, Max, Prefetch, F
from decimal import Decimal
from .models import Product, Category, ProductVariant, ProductImage


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
    
    # Build price filter conditions
    price_conditions = None
    if min_price:
        try:
            min_price_decimal = Decimal(min_price)
            if price_conditions is None:
                price_conditions = Q(variants__price__gte=min_price_decimal)
            else:
                price_conditions &= Q(variants__price__gte=min_price_decimal)
        except (ValueError, TypeError):
            min_price = None
    
    if max_price:
        try:
            max_price_decimal = Decimal(max_price)
            if price_conditions is None:
                price_conditions = Q(variants__price__lte=max_price_decimal)
            else:
                price_conditions &= Q(variants__price__lte=max_price_decimal)
        except (ValueError, TypeError):
            max_price = None
    
    # Apply price filter if any price condition exists
    if price_conditions is not None:
        products = products.filter(price_conditions & Q(variants__is_active=True))

    # Brand filter
    brands = request.GET.getlist("brand")
    if brands:
        products = products.filter(brand__in=brands)

    # Color filter
    colors = request.GET.getlist("color")
    if colors:
        products = products.filter(variants__color__in=colors, variants__is_active=True)

    # Size filter
    sizes = request.GET.getlist("size")
    if sizes:
        products = products.filter(variants__size__in=sizes, variants__is_active=True)

    # Rating filter
    min_rating = request.GET.get("rating")
    if min_rating:
        try:
            min_rating_decimal = Decimal(min_rating)
            # Only show products with reviews (review_count > 0) and rating >= selected
            # Also ensure rating is not 0.0
            products = products.filter(
                review_count__gt=0
            ).filter(
                rating__gte=min_rating_decimal
            ).exclude(
                rating=0.0
            )
        except (ValueError, TypeError):
            min_rating = None

    # On Sale filter
    on_sale = request.GET.get("on_sale")
    if on_sale == "true":
        products = products.filter(
            variants__compare_price__isnull=False,
            variants__compare_price__gt=F("variants__price"),
            variants__is_active=True
        )

    # Sort
    sort_by = request.GET.get("sort", "featured")
    if sort_by == "price_low":
        # Annotate with lowest variant price (already discounted in the price field)
        products = products.annotate(
            lowest_price=Min("variants__price", filter=Q(variants__is_active=True))
        ).order_by("lowest_price")
    elif sort_by == "price_high":
        # Annotate with highest variant price
        products = products.annotate(
            highest_price=Max("variants__price", filter=Q(variants__is_active=True))
        ).order_by("-highest_price")
    elif sort_by == "newest":
        products = products.order_by("-created_at")
    elif sort_by == "name":
        products = products.order_by("name")
    else:  # featured
        products = products.order_by("-is_featured", "-created_at")
    
    # Remove duplicates after all filtering and sorting
    products = products.distinct()

    # Get filter options 
    filter_products = Product.objects.filter(is_active=True)
    
    # Apply same category filter to get relevant options
    if selected_category:
        filter_products = filter_products.filter(category_id__in=category_ids)
    
    # Apply search filter
    if query:
        filter_products = filter_products.filter(
            Q(name__icontains=query)
            | Q(description__icontains=query)
            | Q(category__name__icontains=query)
            | Q(brand__icontains=query)
        )

    # Get available brands from filtered products
    available_brands = (
        filter_products.exclude(brand="")
        .values_list("brand", flat=True)
        .distinct()
        .order_by("brand")
    )
    
    # Check if this is a fashion category to show color/size filters
    available_colors = []
    available_sizes = []
    is_fashion_category = False
    
    if selected_category:
        # Check if current category or its parent is Fashion-related
        fashion_slugs = ['fashion', 'men', 'women', 'kids', 'clothing', 'apparel']
        category_slug_lower = selected_category.slug.lower()
        parent_slug_lower = selected_category.parent.slug.lower() if selected_category.parent else ''
        
        is_fashion_category = (
            category_slug_lower in fashion_slugs or 
            parent_slug_lower in fashion_slugs
        )
    
    if is_fashion_category:
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
    
    # Get user's wishlist items if authenticated
    user_wishlist_ids = []
    if request.user.is_authenticated:
        from accounts.models import Wishlist
        user_wishlist_ids = list(
            Wishlist.objects.filter(user=request.user)
            .values_list('product_id', flat=True)
        )

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
        "user_wishlist_ids": user_wishlist_ids,
        # Filter options
        "available_brands": available_brands,
        "available_colors": available_colors,
        "available_sizes": available_sizes,
        "is_fashion_category": is_fashion_category,  # Flag for fashion categories
        "selected_brands": brands,
        "selected_colors": colors,
        "selected_sizes": sizes,
        "min_price": min_price or "",
        "max_price": max_price or "",
        "price_range": price_range,
        "selected_rating": min_rating or "",
        "selected_on_sale": on_sale or "",
    }

    return render(request, "products/product_list.html", context)


def product_detail(request, slug):
    """Product detail page"""
    product = get_object_or_404(
        Product.objects.prefetch_related(
            Prefetch(
                "variants", queryset=ProductVariant.objects.filter(is_active=True)
            ),
            Prefetch("images", queryset=ProductImage.objects.order_by("display_order")),
        ),
        slug=slug,
        is_active=True,
    )

    # Check if this is a fashion category
    fashion_slugs = ['fashion', 'men', 'women', 'kids', 'clothing', 'apparel']
    category_slug_lower = product.category.slug.lower()
    parent_slug_lower = product.category.parent.slug.lower() if product.category.parent else ''
    
    is_fashion_category = (
        category_slug_lower in fashion_slugs or 
        parent_slug_lower in fashion_slugs
    )

    # Get available colors and sizes for fashion products
    available_colors = []
    available_sizes = []
    if is_fashion_category:
        variants = product.variants.filter(is_active=True)
        available_colors = list(variants.exclude(color="").values_list("color", flat=True).distinct())
        available_sizes = list(variants.exclude(size="").values_list("size", flat=True).distinct())
    
    # Check if product is in user's wishlist
    is_in_wishlist = False
    if request.user.is_authenticated:
        from accounts.models import Wishlist
        is_in_wishlist = Wishlist.objects.filter(
            user=request.user,
            product=product
        ).exists()

    context = {
        "product": product,
        "is_fashion_category": is_fashion_category,
        "available_colors": available_colors,
        "available_sizes": available_sizes,
        "is_in_wishlist": is_in_wishlist,
    }
    return render(request, "products/product_detail.html", context)


def category_list(request, slug):
    """List products by category"""
    category = get_object_or_404(Category, slug=slug)
    products = Product.objects.filter(
        category=category, is_active=True
    ).prefetch_related(
        Prefetch("variants", queryset=ProductVariant.objects.filter(is_active=True)),
        Prefetch("images", queryset=ProductImage.objects.order_by("display_order")),
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
        Prefetch("images", queryset=ProductImage.objects.order_by("display_order")),
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
