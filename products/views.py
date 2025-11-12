from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Q, Min, Prefetch
from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from products.models import (
    Product,
    ProductVariant,
    ProductImage,
    Category,
)
from reviews.models import Review
from products.forms import ReviewForm
from products.utils import update_product_rating
from django.http import JsonResponse
from orders.models import Order


def product_list(request):
    """Product list page with filtering"""
    # Get query parameters
    category_slug = request.GET.get("category")
    min_price = request.GET.get("min_price")
    max_price = request.GET.get("max_price")
    sort_field = request.GET.get("sort", "created")  # Default field: created
    sort_direction = request.GET.get("direction", "desc")  # Default direction: descending
    on_sale = request.GET.get("on_sale")
    query = request.GET.get("q", "").strip()  # Search query

    # Base queryset - only show products with at least one active variant
    products = Product.objects.filter(
        is_active=True,
        variants__is_active=True
    ).distinct().prefetch_related(
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

    # Filter by on sale
    if on_sale == "true":
        products = products.filter(variants__compare_price__isnull=False).distinct()

    # Filter by rating
    rating = request.GET.get("rating")
    if rating:
        try:
            rating_value = float(rating)
            products = products.filter(rating__gte=rating_value)
        except (ValueError, TypeError):
            pass

    # Get all parent categories for filter with product counts
    categories = list(
        Category.objects.filter(parent__isnull=True, is_active=True)
        .prefetch_related('children')
    )
    
    # Add product counts to each category (including subcategories)
    for category in categories:
        # Fetch children into a list so we can add attributes to them
        children_list = list(category.children.filter(is_active=True))

        # Get this category and all its children IDs
        cat_ids = [category.id]
        cat_ids.extend([child.id for child in children_list])
        
        # Count products with active variants for parent (includes all children)
        category.product_count = Product.objects.filter(
            is_active=True,
            category_id__in=cat_ids,
            variants__is_active=True
        ).distinct().count()

        # Add counts to each child category
        for child in children_list:
            child.product_count = Product.objects.filter(
                is_active=True,
                category_id=child.id,
                variants__is_active=True
            ).distinct().count()
        
        # Replace the queryset with our list that has counts
        category.children_with_counts = children_list

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

    # Get available brands with counts based on currently filtered products
    # This ensures brands are contextual to the selected category
    from django.db.models import Count
    
    # Start with the current product queryset (which already has category filter applied)
    brand_query = products
    
    # Get brand counts from filtered products
    brand_counts = (
        brand_query
        .exclude(brand='')
        .values('brand')
        .annotate(count=Count('id', distinct=True))
        .order_by('brand')
    )
    
    # Convert to list of dicts with brand and count, filter out 0 counts
    available_brands = [
        {'name': item['brand'], 'count': item['count']} 
        for item in brand_counts
        if item['count'] > 0
    ]
    
    # Filter products by selected brands if any
    if selected_brands:
        products = products.filter(brand__in=selected_brands)
    
    # Get available colors and sizes for fashion categories (based on current filters)
    available_colors = []
    available_sizes = []
    if is_fashion_category:
        # Get from current filtered products (before applying color/size filters)
        color_size_query = products
        
        variant_qs = ProductVariant.objects.filter(
            product__in=color_size_query, 
            is_active=True
        )
        
        # Get colors with counts
        color_counts = (
            variant_qs.exclude(color='')
            .values('color')
            .annotate(count=Count('product', distinct=True))
            .order_by('color')
        )
        available_colors = [
            {'name': item['color'], 'count': item['count']}
            for item in color_counts
            if item['count'] > 0
        ]
        
        # Get sizes with counts
        size_counts = (
            variant_qs.exclude(size='')
            .values('size')
            .annotate(count=Count('product', distinct=True))
            .order_by('size')
        )
        available_sizes = [
            {'name': item['size'], 'count': item['count']}
            for item in size_counts
            if item['count'] > 0
        ]
        
        # Filter by selected colors/sizes
        if selected_colors:
            products = products.filter(variants__color__in=selected_colors).distinct()
        if selected_sizes:
            products = products.filter(variants__size__in=selected_sizes).distinct()

    # Sorting - build order based on field and direction
    sort_field_map = {
        "name": "name",
        "price": "variants__price",
        "created": "created_at",
        "rating": "rating",
    }
    
    # Get the field to sort by
    order_field = sort_field_map.get(sort_field, "created_at")
    
    # Apply direction (asc or desc)
    if sort_direction == "asc":
        order_by = order_field
    else:  # desc
        order_by = f"-{order_field}"
    
    products = products.order_by(order_by).distinct()

    # Pagination
    paginator = Paginator(products, 12)  # 12 products per page
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

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
        "sort_field": sort_field,
        "sort_direction": sort_direction,
        "selected_min_price": min_price or "",
        "selected_max_price": max_price or "",
        "selected_on_sale": on_sale or "",
        "selected_rating": rating or "",
        "selected_brands": selected_brands,
        "selected_colors": selected_colors,
        "selected_sizes": selected_sizes,
        "query": query,  # Add search query to context
        "is_fashion_category": is_fashion_category,
        "available_brands": available_brands,
        "available_colors": available_colors,
        "available_sizes": available_sizes,
        "price_range": None,  # Can be calculated if needed
        "query_string": query_string,
    }

    return render(request, "products/product_list.html", context)


def product_detail(request, sku):
    """Product detail page"""
    product = get_object_or_404(
        Product.objects.prefetch_related(
            Prefetch(
                "variants", queryset=ProductVariant.objects.filter(is_active=True)
            ),
            Prefetch("images", queryset=ProductImage.objects.order_by("display_order")),
        ),
        sku=sku,
        is_active=True,
    )

    # Track product view for authenticated users
    if request.user.is_authenticated:
        from accounts.models import BrowsingHistory
        from django.db.models import F
        
        browsing_history, created = BrowsingHistory.objects.get_or_create(
            user=request.user,
            product=product
        )
        if not created:
            # Increment view count if entry already exists
            browsing_history.view_count = F('view_count') + 1
            browsing_history.save(update_fields=['view_count', 'viewed_at'])

    # Check if this is a fashion category
    fashion_slugs = ['fashion', 'men', 'women', 'kids', 'clothing', 'apparel']
    category_slug_lower = product.category.slug.lower()
    parent_slug_lower = product.category.parent.slug.lower() if product.category.parent else ''
    
    # Check if category or parent slug contains any fashion keyword
    is_fashion_category = (
        any(keyword in category_slug_lower for keyword in fashion_slugs) or
        any(keyword in parent_slug_lower for keyword in fashion_slugs)
    )

    # Get available colors and sizes for fashion products
    # Always show the selected color and size from the current variant
    available_colors = []
    available_sizes = []
    selected_color = None
    selected_size = None
    
    if is_fashion_category:
        variants = product.variants.filter(is_active=True)
        
        # Get the current variant (lowest priced variant)
        lowest_variant = product.get_lowest_priced_variant()
        if lowest_variant:
            selected_color = lowest_variant.color or ""
            selected_size = lowest_variant.size or ""
        
        # Always show variant selectors if variants exist
        if variants.exists():
            # Get all distinct colors (including empty strings) - use set to ensure uniqueness
            color_set = set()
            for variant in variants:
                color = variant.color if variant.color else ""
                color_set.add(color)
            color_list = sorted(list(color_set))  # Sort for consistent display
            
            # Always include the selected color
            if selected_color is not None:
                selected_color_str = selected_color if selected_color else ""
                if selected_color_str not in color_list:
                    available_colors = [selected_color_str] + color_list
                else:
                    available_colors = color_list if color_list else [""]
            elif color_list:
                available_colors = color_list
            else:
                # If no colors but variants exist, show empty string as option
                available_colors = [""]
            
            # Get all distinct sizes (including empty strings) - use set to ensure uniqueness
            size_set = set()
            for variant in variants:
                size = variant.size if variant.size else ""
                size_set.add(size)
            # Sort sizes in a logical order
            size_order = ["XS", "S", "M", "L", "XL", "XXL", ""]
            size_list = sorted(list(size_set), key=lambda x: (size_order.index(x) if x in size_order else 999, x))
            
            # Always include the selected size
            if selected_size is not None:
                selected_size_str = selected_size if selected_size else ""
                if selected_size_str not in size_list:
                    available_sizes = [selected_size_str] + size_list
                else:
                    available_sizes = size_list if size_list else [""]
            elif size_list:
                available_sizes = size_list
            else:
                # If no sizes but variants exist, show empty string as option
                available_sizes = [""]
    
    # Check if product is in user's wishlist
    is_in_wishlist = False
    if request.user.is_authenticated:
        from accounts.models import Wishlist
        is_in_wishlist = Wishlist.objects.filter(
            user=request.user,
            product=product
        ).exists()

    # Review functionality
    reviews_list = product.reviews.select_related('user').all()
    
    # Sort reviews based on query parameter (matching products page style)
    sort_field = request.GET.get('sort', 'created')  # Default: created (most recent)
    sort_direction = request.GET.get('direction', 'desc')  # Default: descending
    
    if sort_field == 'rating':
        if sort_direction == 'asc':
            reviews_list = reviews_list.order_by('rating', '-created_at')  # Lowest rating first
        else:  # desc
            reviews_list = reviews_list.order_by('-rating', '-created_at')  # Highest rating first
    else:  # 'created' (default - most recent)
        if sort_direction == 'asc':
            reviews_list = reviews_list.order_by('created_at')  # Oldest first
        else:  # desc
            reviews_list = reviews_list.order_by('-created_at')  # Most recent first
    
    # Check if user can review this product
    can_review = False
    existing_review = None
    has_purchased = False
    
    if request.user.is_authenticated:
        # Check if user has an existing review
        existing_review = product.reviews.filter(user=request.user).first()
        
        # Check if user has a delivered/completed order containing this product
        has_purchased = Order.objects.filter(
            user=request.user,
            status__in=['delivered', 'completed'],
            items__product=product
        ).exists()
        
        # User can review if they've purchased and don't have a review yet
        can_review = has_purchased

    context = {
        "product": product,
        "is_fashion_category": is_fashion_category,
        "available_colors": available_colors,
        "available_sizes": available_sizes,
        "selected_color": selected_color,
        "selected_size": selected_size,
        "is_in_wishlist": is_in_wishlist,
        "reviews": reviews_list,
        "review_count": reviews_list.count(),
        "can_review": can_review,
        "existing_review": existing_review,
        "has_purchased": has_purchased,
        "sort_field": sort_field,
        "sort_direction": sort_direction,
    }

    return render(request, "products/product_detail.html", context)


def get_reviews_ajax(request, sku):
    """AJAX endpoint to get sorted reviews for a product"""
    from django.template.loader import render_to_string
    from django.http import JsonResponse
    
    product = get_object_or_404(Product, sku=sku, is_active=True)
    
    # Get sort parameters
    sort_field = request.GET.get('sort', 'created')
    sort_direction = request.GET.get('direction', 'desc')
    
    # Get and sort reviews
    reviews_list = product.reviews.select_related('user').all()
    
    if sort_field == 'rating':
        if sort_direction == 'asc':
            reviews_list = reviews_list.order_by('rating', '-created_at')
        else:  # desc
            reviews_list = reviews_list.order_by('-rating', '-created_at')
    else:  # 'created' (default)
        if sort_direction == 'asc':
            reviews_list = reviews_list.order_by('created_at')
        else:  # desc
            reviews_list = reviews_list.order_by('-created_at')
    
    # Render reviews HTML
    reviews_html = render_to_string('products/reviews_list.html', {
        'reviews': reviews_list,
        'product': product,
        'user': request.user,
    }, request=request)
    
    # Render updated sort buttons HTML
    sort_buttons_html = render_to_string('products/review_sort_buttons.html', {
        'sort_field': sort_field,
        'sort_direction': sort_direction,
        'product': product,
    }, request=request)
    
    return JsonResponse({
        'success': True,
        'html': reviews_html,
        'sort_buttons_html': sort_buttons_html,
        'sort_field': sort_field,
        'sort_direction': sort_direction,
    })


def category_list(request, slug):
    """Category page"""
    category = get_object_or_404(Category, slug=slug, is_active=True)

    # Redirect to product list with category filter
    from django.shortcuts import redirect
    return redirect(f"/products/?category={slug}")


def search(request):
    """Search products"""
    query = request.GET.get("q", "")
    products = Product.objects.filter(
        is_active=True,
        variants__is_active=True
    ).distinct().prefetch_related(
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


def search_suggestions(request):
    """AJAX endpoint for search suggestions"""
    query = request.GET.get("q", "").strip()
    
    if len(query) < 2:
        return JsonResponse({"suggestions": []})
    
    # Get up to 5 product suggestions
    products = Product.objects.filter(
        is_active=True,
        variants__is_active=True
    ).filter(
        Q(name__icontains=query)
        | Q(brand__icontains=query)
        | Q(category__name__icontains=query)
    ).distinct()[:5]
    
    suggestions = []
    for product in products:
        try:
            image = product.get_primary_image()
            
            # Safely get image URL
            image_url = None
            if image and hasattr(image, 'image') and image.image:
                try:
                    image_url = image.image.url
                except (AttributeError, ValueError):
                    image_url = None
            
            lowest_variant = product.get_lowest_priced_variant()
            price = float(lowest_variant.price) if lowest_variant else 0.0
            
            suggestions.append({
                "id": product.id,
                "name": product.name,
                "slug": product.slug,
                "sku": product.sku,
                "brand": product.brand or "",
                "category": product.category.name if product.category else "",
                "image": image_url,
                "price": price,
            })
        except Exception:
            # Skip products that fail to serialize
            continue
    
    return JsonResponse({"suggestions": suggestions})


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


@login_required
def submit_review(request, sku):
    """Submit or edit a product review"""
    product = get_object_or_404(Product, sku=sku, is_active=True)
    
    # Check if user has purchased this product
    has_purchased = Order.objects.filter(
        user=request.user,
        status__in=['delivered', 'completed'],
        items__product=product
    ).exists()
    
    if not has_purchased:
        messages.error(request, "You can only review products you have purchased and received.")
        return redirect('products:product_detail', sku=sku)
    
    # Check if user already has a review
    existing_review = Review.objects.filter(user=request.user, product=product).first()
    
    if request.method == 'POST':
        form = ReviewForm(request.POST, instance=existing_review)
        if form.is_valid():
            review = form.save(commit=False)
            review.user = request.user
            review.product = product
            review.is_verified_purchase = True
            review.save()
            
            # Update product rating after saving review
            update_product_rating(product)
            
            if existing_review:
                messages.success(request, "Your review has been updated successfully!")
            else:
                messages.success(request, "Thank you for your review!")
            
            return redirect('products:product_detail', sku=sku)
    else:
        form = ReviewForm(instance=existing_review)
    
    context = {
        'product': product,
        'form': form,
        'existing_review': existing_review,
    }
    
    return render(request, 'products/submit_review.html', context)


@login_required
def delete_review(request, review_id):
    """Delete a user's review"""
    review = get_object_or_404(Review, id=review_id, user=request.user)
    product = review.product
    product_sku = product.sku
    
    if request.method == 'POST':
        review.delete()
        
        # Update product rating after deleting review
        update_product_rating(product)
        
        messages.success(request, "Your review has been deleted.")
        return redirect('products:product_detail', sku=product_sku)
    
    # If not POST, redirect back to product page
    return redirect('products:product_detail', sku=product_sku)
