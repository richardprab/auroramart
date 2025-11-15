from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from products.models import Product
from .services import CustomerCategoryPredictor, ProductRecommender, PersonalizedRecommendations


@require_http_methods(["GET"])
@login_required
def predict_user_category(request):
    """Predict user's preferred category based on demographics"""
    from accounts.models import Customer
    
    user = request.user
    
    # Check if user is a Customer instance
    # Since AUTH_USER_MODEL is Customer, request.user is usually a Customer instance
    customer = user if isinstance(user, Customer) else None
    
    if not customer or not customer.age or not customer.gender:
        return JsonResponse({
            'error': 'User demographics incomplete. Please complete your profile.'
        }, status=400)
    
    try:
        predicted_category = CustomerCategoryPredictor.predict(customer)
        return JsonResponse({
            'predicted_category': predicted_category,
            'user': {
                'age': customer.age,
                'gender': customer.gender,
                'occupation': customer.occupation,
                'education': customer.education,
            }
        })
    except Exception as e:
        return JsonResponse({
            'error': str(e)
        }, status=500)


@require_http_methods(["GET"])
def get_similar_products(request, product_id):
    """Get products frequently bought with the specified product"""
    try:
        product = Product.objects.get(id=product_id, is_active=True)
    except Product.DoesNotExist:
        return JsonResponse({
            'error': 'Product not found'
        }, status=404)
    
    top_n = int(request.GET.get('limit', 5))
    
    try:
        recommendations = ProductRecommender.get_recommendations(product, top_n=top_n)
        
        # Serialize products manually
        recommendations_data = []
        for prod in recommendations:
            try:
                default_variant = prod.get_lowest_priced_variant()
                image = prod.get_primary_image()
                
                # Convert rating properly - handle DecimalField
                rating_value = 0.0
                if prod.rating is not None:
                    try:
                        rating_value = float(prod.rating)
                    except (TypeError, ValueError):
                        rating_value = 0.0
                
                # Safely get image URL
                image_url = None
                image_alt = prod.name
                if image:
                    try:
                        if hasattr(image, 'image') and image.image:
                            image_url = image.image.url
                        if hasattr(image, 'alt_text') and image.alt_text:
                            image_alt = image.alt_text
                    except (AttributeError, ValueError):
                        image_url = None
                
                # Safely get variant price
                variant_price = 0.0
                variant_compare_price = None
                variant_stock = 0
                variant_id = None
                if default_variant:
                    try:
                        variant_id = default_variant.id
                        from products.pricing import get_effective_price
                        variant_price = float(get_effective_price(default_variant))
                        if default_variant.compare_price:
                            variant_compare_price = float(default_variant.compare_price)
                        variant_stock = default_variant.stock if default_variant.stock else 0
                    except (AttributeError, ValueError, TypeError):
                        variant_price = 0.0
                        variant_stock = 0
                
                recommendations_data.append({
                    'id': prod.id,
                    'name': prod.name,
                    'slug': prod.slug,
                    'sku': prod.sku,
                    'brand': prod.brand or '',
                    'rating': rating_value,
                    'primary_image': {
                        'url': image_url,
                        'alt_text': image_alt
                    } if image_url else None,
                    'lowest_variant': {
                        'id': variant_id,
                        'price': variant_price,
                        'compare_price': variant_compare_price,
                        'stock': variant_stock,
                    } if variant_id else None
                })
            except Exception as e:
                # Skip products that fail to serialize
                continue
        
        return JsonResponse({
            'product': {
                'id': product.id,
                'name': product.name,
                'sku': product.sku,
            },
            'recommendations': recommendations_data,
            'count': len(recommendations_data)
        })
    except Exception as e:
        return JsonResponse({
            'error': str(e),
            'recommendations': [],
            'count': 0
        }, status=500)


@require_http_methods(["POST", "GET"])
@login_required
def get_cart_recommendations(request):
    """Get product recommendations based on cart contents"""
    from cart.models import CartItem, Cart
    
    # Get user's cart
    try:
        cart = Cart.objects.get(user=request.user)
    except Cart.DoesNotExist:
        return JsonResponse({
            'recommendations': [],
            'message': 'Cart is empty'
        })
    
    cart_items = CartItem.objects.filter(
        cart=cart
    ).select_related('product_variant__product', 'product')
    
    if not cart_items.exists():
        return JsonResponse({
            'recommendations': [],
            'message': 'Cart is empty'
        })
    
    # Get limit from request, default to 20 (show all recommendations)
    top_n = int(request.GET.get('limit', request.POST.get('limit', 20)))
    
    try:
        recommendations = ProductRecommender.get_recommendations(cart_items, top_n=top_n)
        
        # Serialize products manually
        recommendations_data = []
        for prod in recommendations:
            try:
                default_variant = prod.get_lowest_priced_variant()
                image = prod.get_primary_image()
                
                # Safely get image URL
                image_url = None
                if image and hasattr(image, 'image') and image.image:
                    try:
                        image_url = image.image.url
                    except (AttributeError, ValueError):
                        image_url = None
                
                recommendations_data.append({
                    'id': prod.id,
                    'name': prod.name,
                    'slug': prod.slug,
                    'sku': prod.sku,
                    'brand': prod.brand,
                    'rating': float(prod.rating) if prod.rating else 0.0,
                    'review_count': prod.reviews.count(),
                    'primary_image': {
                        'url': image_url,
                        'alt_text': image.alt_text if image else prod.name
                    } if image else None,
                    'lowest_variant': {
                        'id': default_variant.id if default_variant else None,
                        'price': float(default_variant.price) if default_variant else 0.0,
                        'compare_price': float(default_variant.compare_price) if default_variant and default_variant.compare_price else None,
                        'stock': default_variant.stock if default_variant else 0,
                    } if default_variant else None
                })
            except Exception:
                # Skip products that fail to serialize
                continue
        
        return JsonResponse({
            'recommendations': recommendations_data,
            'count': len(recommendations)
        })
    except Exception as e:
        return JsonResponse({
            'error': str(e)
        }, status=500)


@require_http_methods(["GET"])
def get_personalized_recommendations(request):
    """Get personalized product recommendations for the user"""
    limit = int(request.GET.get('limit', 10))
    
    try:
        if request.user.is_authenticated:
            recommendations = PersonalizedRecommendations.get_for_user(request.user, limit=limit)
            # Get user's wishlist product IDs
            from accounts.models import Wishlist
            user_wishlist_ids = set(
                Wishlist.objects.filter(user=request.user)
                .values_list('product_id', flat=True)
            )
        else:
            recommendations = PersonalizedRecommendations.get_for_user(None, limit=limit)
            user_wishlist_ids = set()
        
        # Serialize products manually
        recommendations_data = []
        for prod in recommendations:
            try:
                default_variant = prod.get_lowest_priced_variant()
                image = prod.get_primary_image()
                
                # Safely get image URL
                image_url = None
                if image and hasattr(image, 'image') and image.image:
                    try:
                        image_url = image.image.url
                    except (AttributeError, ValueError):
                        image_url = None
                
                recommendations_data.append({
                    'id': prod.id,
                    'name': prod.name,
                    'slug': prod.slug,
                    'sku': prod.sku,
                    'brand': prod.brand,
                    'rating': float(prod.rating) if prod.rating else 0.0,
                    'review_count': prod.reviews.count(),
                    'is_in_wishlist': prod.id in user_wishlist_ids,
                    'primary_image': {
                        'url': image_url,
                        'alt_text': image.alt_text if image else prod.name
                    } if image else None,
                    'lowest_variant': {
                        'id': default_variant.id if default_variant else None,
                        'price': float(default_variant.price) if default_variant else 0.0,
                        'compare_price': float(default_variant.compare_price) if default_variant and default_variant.compare_price else None,
                        'stock': default_variant.stock if default_variant else 0,
                    } if default_variant else None
                })
            except Exception:
                # Continue with other products even if one fails
                pass
        
        # Check if user is a Customer with demographic data
        # Since AUTH_USER_MODEL is Customer, request.user is usually a Customer instance
        from accounts.models import Customer
        customer = request.user if isinstance(request.user, Customer) else None
        has_demographics = customer and bool(customer.age) if customer else False
        
        return JsonResponse({
            'recommendations': recommendations_data,
            'count': len(recommendations),
            'personalized': request.user.is_authenticated and has_demographics
        })
    except Exception as e:
        return JsonResponse({
            'error': str(e)
        }, status=500)
