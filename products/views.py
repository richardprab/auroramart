from django.shortcuts import render, get_object_or_404
from django.db.models import Q, Min, Prefetch
from django.core.paginator import Paginator
from products.models import (
    Product,
    ProductVariant,
    ProductImage,
    Category,
)
from django.http import JsonResponse


def product_list(request):
    """Product list page with filtering"""
    # Get query parameters
    category_slug = request.GET.get("category")
    min_price = request.GET.get("min_price")
    max_price = request.GET.get("max_price")
    sort_by = request.GET.get("sort", "created")  # Default to newest
    on_sale = request.GET.get("on_sale")
    query = request.GET.get("q", "").strip()  # Search query
    selected_rating = request.GET.get("rating", "")

    # Base queryset
    products = Product.objects.filter(is_active=True).prefetch_related(
        Prefetch("variants", queryset=ProductVariant.objects.filter(is_active=True)),
        Prefetch("images", queryset=ProductImage.objects.order_by("display_order")),
    )

    # Filter by search query
    if query:
        products = products.filter(
            Q(name__icontains=query)
            | Q(description__icontains=query)
            | Q(brand__icontains=query)
            | Q(category__name__icontains=query)
            | Q(sku__icontains=query)
        )

    # Filter by category
    selected_category = None
    if category_slug:
        selected_category = get_object_or_404(Category, slug=category_slug)
        # Include subcategories
        category_ids = [selected_category.id]
        category_ids.extend(
            selected_category.children.values_list("id", flat=True)
        )
        products = products.filter(category_id__in=category_ids)

    # Filter by price range
    if min_price:
        try:
            min_price = float(min_price)
            products = products.annotate(
                min_variant_price=Min("variants__price")
            ).filter(min_variant_price__gte=min_price)
        except (ValueError, TypeError):
            pass
    if max_price:
        try:
            max_price = float(max_price)
            products = products.annotate(
                max_variant_price=Min("variants__price")
            ).filter(max_variant_price__lte=max_price)
        except (ValueError, TypeError):
            pass

    # Filter by rating
    if selected_rating:
        try:
            rating_value = float(selected_rating)
            products = products.filter(rating__gte=rating_value)
        except (ValueError, TypeError):
            pass

    # Filter by on sale
    if on_sale == "true":
        products = products.filter(variants__compare_price__isnull=False).distinct()

    # Sorting
    sort_options = {
        "price_asc": "variants__price",
        "price_desc": "-variants__price",
        "name": "name",
        "rating": "-rating",
        "created": "-created_at",
        "featured": "-is_featured",
        "newest": "-created_at",
        "price_low": "variants__price",
        "price_high": "-variants__price",
    }
    products = products.order_by(sort_options.get(sort_by, "-created_at")).distinct()

    # Pagination
    paginator = Paginator(products, 12)  # 12 products per page
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    # Get all parent categories for filter
    categories = Category.objects.filter(parent__isnull=True, is_active=True)

    # Get filter parameters
    selected_brands = request.GET.getlist("brand", [])
    selected_colors = request.GET.getlist("color", [])
    selected_sizes = request.GET.getlist("size", [])
    
    # Check if fashion category
    is_fashion_category = False
    if selected_category:
        fashion_slugs = ['fashion', 'men', 'women', 'kids', 'clothing', 'apparel']
        category_slug_lower = selected_category.slug.lower()
        parent_slug_lower = selected_category.parent.slug.lower() if selected_category.parent else ''
        is_fashion_category = (
            category_slug_lower in fashion_slugs or 
            parent_slug_lower in fashion_slugs
        )
    
    # Build query string for pagination
    query_params = request.GET.copy()
    if 'page' in query_params:
        del query_params['page']
    query_string = query_params.urlencode()

    context = {
        "page_obj": page_obj,
        "products": products,  # Keep for backwards compatibility
        "categories": categories,
        "selected_category": selected_category,
        "selected_sort": sort_by,
        "selected_min_price": min_price or "",
        "selected_max_price": max_price or "",
        "selected_on_sale": on_sale or "",
        "selected_brands": selected_brands,
        "selected_colors": selected_colors,
        "selected_sizes": selected_sizes,
        "selected_rating": selected_rating,
        "query": query,  # Add search query to context
        "is_fashion_category": is_fashion_category,
        "available_brands": [],  # Can be populated if needed
        "available_colors": [],  # Can be populated if needed
        "available_sizes": [],  # Can be populated if needed
        "price_range": None,  # Can be calculated if needed
        "query_string": query_string,
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
    """Category page"""
    category = get_object_or_404(Category, slug=slug, is_active=True)

    # Redirect to product list with category filter
    from django.shortcuts import redirect
    return redirect(f"/products/?category={slug}")


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


def product_detail_ajax(request, product_id):
    """AJAX endpoint for product quick view (replacing DRF API)"""
    try:
        product = Product.objects.get(id=product_id, is_active=True)
        default_variant = product.get_lowest_priced_variant()
        image = product.get_primary_image()
        
        # Get all variants
        variants_data = []
        for variant in product.variants.filter(is_active=True):
            variants_data.append({
                'id': variant.id,
                'sku': variant.sku,
                'color': variant.color,
                'size': variant.size,
                'price': float(variant.price),
                'compare_price': float(variant.compare_price) if variant.compare_price else None,
                'stock': variant.stock,
            })
        
        data = {
            'id': product.id,
            'name': product.name,
            'slug': product.slug,
            'sku': product.sku,
            'brand': product.brand,
            'description': product.description,
            'rating': float(product.rating) if product.rating else 0.0,
            'review_count': product.review_count,
            'image': image.image.url if image else None,
            'price': float(default_variant.price) if default_variant else 0.0,
            'compare_price': float(default_variant.compare_price) if default_variant and default_variant.compare_price else None,
            'variants': variants_data,
            'category': {
                'id': product.category.id,
                'name': product.category.name,
                'slug': product.category.slug,
            } if product.category else None,
        }
        
        return JsonResponse(data)
    except Product.DoesNotExist:
        return JsonResponse({'error': 'Product not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
