from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from products.models import Product
from .services import CustomerCategoryPredictor, ProductRecommender, PersonalizedRecommendations


@require_http_methods(["GET"])
@login_required
def predict_user_category(request):
    """Predict user's preferred category based on demographics"""
    user = request.user
    
    if not user.age_range or not user.gender:
        return JsonResponse({
            'error': 'User demographics incomplete. Please complete your profile.'
        }, status=400)
    
    try:
        predicted_category = CustomerCategoryPredictor.predict(user)
        return JsonResponse({
            'predicted_category': predicted_category,
            'user': {
                'age_range': user.age_range,
                'gender': user.gender,
                'occupation': user.occupation,
                'education': user.education,
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
        recommendations = ProductRecommender.get_similar_products(product, top_n=top_n)
        
        # Serialize products manually
        recommendations_data = []
        for prod in recommendations:
            default_variant = prod.get_lowest_priced_variant()
            image = prod.get_primary_image()
            
            recommendations_data.append({
                'id': prod.id,
                'name': prod.name,
                'slug': prod.slug,
                'sku': prod.sku,
                'brand': prod.brand,
                'rating': float(prod.rating) if prod.rating else 0.0,
                'review_count': prod.review_count,
                'primary_image': {
                    'url': image.image.url if image else None,
                    'alt_text': image.alt_text if image else prod.name
                } if image else None,
                'lowest_variant': {
                    'price': float(default_variant.price) if default_variant else 0.0,
                    'compare_price': float(default_variant.compare_price) if default_variant and default_variant.compare_price else None,
                } if default_variant else None
            })
        
        return JsonResponse({
            'product': {
                'id': product.id,
                'name': product.name,
                'sku': product.sku,
            },
            'recommendations': recommendations_data,
            'count': len(recommendations)
        })
    except Exception as e:
        return JsonResponse({
            'error': str(e)
        }, status=500)


@require_http_methods(["POST", "GET"])
@login_required
def get_cart_recommendations(request):
    """Get product recommendations based on cart contents"""
    from cart.models import CartItem
    
    cart_items = CartItem.objects.filter(
        user=request.user
    ).select_related('product_variant__product')
    
    if not cart_items.exists():
        return JsonResponse({
            'recommendations': [],
            'message': 'Cart is empty'
        })
    
    top_n = int(request.GET.get('limit', request.POST.get('limit', 5)))
    
    try:
        recommendations = ProductRecommender.get_cart_recommendations(cart_items, top_n=top_n)
        
        # Serialize products manually
        recommendations_data = []
        for prod in recommendations:
            default_variant = prod.get_lowest_priced_variant()
            image = prod.get_primary_image()
            
            recommendations_data.append({
                'id': prod.id,
                'name': prod.name,
                'slug': prod.slug,
                'sku': prod.sku,
                'brand': prod.brand,
                'rating': float(prod.rating) if prod.rating else 0.0,
                'review_count': prod.review_count,
                'primary_image': {
                    'url': image.image.url if image else None,
                    'alt_text': image.alt_text if image else prod.name
                } if image else None,
                'lowest_variant': {
                    'price': float(default_variant.price) if default_variant else 0.0,
                    'compare_price': float(default_variant.compare_price) if default_variant and default_variant.compare_price else None,
                } if default_variant else None
            })
        
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
        else:
            recommendations = PersonalizedRecommendations.get_for_user(None, limit=limit)
        
        # Serialize products manually
        recommendations_data = []
        for prod in recommendations:
            default_variant = prod.get_lowest_priced_variant()
            image = prod.get_primary_image()
            
            recommendations_data.append({
                'id': prod.id,
                'name': prod.name,
                'slug': prod.slug,
                'sku': prod.sku,
                'brand': prod.brand,
                'rating': float(prod.rating) if prod.rating else 0.0,
                'review_count': prod.review_count,
                'primary_image': {
                    'url': image.image.url if image else None,
                    'alt_text': image.alt_text if image else prod.name
                } if image else None,
                'lowest_variant': {
                    'price': float(default_variant.price) if default_variant else 0.0,
                    'compare_price': float(default_variant.compare_price) if default_variant and default_variant.compare_price else None,
                } if default_variant else None
            })
        
        return JsonResponse({
            'recommendations': recommendations_data,
            'count': len(recommendations),
            'personalized': request.user.is_authenticated and bool(request.user.age_range)
        })
    except Exception as e:
        return JsonResponse({
            'error': str(e)
        }, status=500)
