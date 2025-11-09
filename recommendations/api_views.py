from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status
from products.serializers import ProductListSerializer
from products.models import Product
from .services import CustomerCategoryPredictor, ProductRecommender, PersonalizedRecommendations


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def predict_user_category(request):
    """Predict user's preferred category based on demographics"""
    user = request.user
    
    if not user.age_range or not user.gender:
        return Response({
            'error': 'User demographics incomplete. Please complete your profile.'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        predicted_category = CustomerCategoryPredictor.predict(user)
        return Response({
            'predicted_category': predicted_category,
            'user': {
                'age_range': user.age_range,
                'gender': user.gender,
                'occupation': user.occupation,
                'education': user.education,
            }
        })
    except Exception as e:
        return Response({
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def get_similar_products(request, product_id):
    """Get products frequently bought with the specified product"""
    try:
        product = Product.objects.get(id=product_id, is_active=True)
    except Product.DoesNotExist:
        return Response({
            'error': 'Product not found'
        }, status=status.HTTP_404_NOT_FOUND)
    
    top_n = int(request.GET.get('limit', 5))
    
    try:
        recommendations = ProductRecommender.get_similar_products(product, top_n=top_n)
        serializer = ProductListSerializer(recommendations, many=True, context={'request': request})
        
        return Response({
            'product': {
                'id': product.id,
                'name': product.name,
                'sku': product.sku,
            },
            'recommendations': serializer.data,
            'count': len(recommendations)
        })
    except Exception as e:
        return Response({
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([AllowAny])
def get_cart_recommendations(request):
    """Get product recommendations based on cart contents"""
    from cart.models import Cart, CartItem
    
    # Get cart for both authenticated and guest users
    if request.user.is_authenticated:
        try:
            cart = Cart.objects.get(user=request.user)
        except Cart.DoesNotExist:
            return Response({
                'recommendations': [],
                'message': 'Cart is empty'
            })
    else:
        session_key = request.session.session_key
        if not session_key:
            return Response({
                'recommendations': [],
                'message': 'No session cart found'
            })
        try:
            cart = Cart.objects.get(session_key=session_key)
        except Cart.DoesNotExist:
            return Response({
                'recommendations': [],
                'message': 'Cart is empty'
            })
    
    # Get items from cart
    cart_items = cart.items.select_related(
        'product_variant__product',
        'product'
    ).all()
    
    if not cart_items.exists():
        return Response({
            'recommendations': [],
            'message': 'Cart is empty'
        })
    
    top_n = int(request.data.get('limit', 5))
    
    try:
        # DEBUG: Print cart items info
        print(f"DEBUG: Cart has {cart_items.count()} items")
        for item in cart_items:
            print(f"DEBUG: Item - Product: {item.product.name if item.product else 'None'}, SKU: {item.product.sku if item.product else 'None'}")
            if item.product_variant:
                print(f"DEBUG: Variant SKU: {item.product_variant.sku}")
        
        recommendations = ProductRecommender.get_cart_recommendations(cart_items, top_n=top_n)
        
        # DEBUG: Print recommendations
        print(f"DEBUG: Got {len(recommendations)} recommendations")
        for rec in recommendations:
            print(f"DEBUG: Recommendation - {rec.name}, SKU: {rec.sku}")
        
        # Filter out products already in cart
        cart_product_ids = set(item.product.id for item in cart_items if item.product)
        recommendations = [p for p in recommendations if p.id not in cart_product_ids]
        
        print(f"DEBUG: After filtering: {len(recommendations)} recommendations")
        
        serializer = ProductListSerializer(recommendations, many=True, context={'request': request})
        
        return Response({
            'recommendations': serializer.data,
            'count': len(recommendations)
        })
    except Exception as e:
        print(f"DEBUG ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return Response({
            'error': str(e),
            'recommendations': []
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def get_personalized_recommendations(request):
    """Get personalized product recommendations for the user"""
    limit = int(request.GET.get('limit', 10))
    
    try:
        if request.user.is_authenticated:
            recommendations = PersonalizedRecommendations.get_for_user(request.user, limit=limit)
        else:
            recommendations = PersonalizedRecommendations.get_for_user(None, limit=limit)
        
        serializer = ProductListSerializer(recommendations, many=True, context={'request': request})
        
        return Response({
            'recommendations': serializer.data,
            'count': len(recommendations),
            'personalized': request.user.is_authenticated and bool(request.user.age_range)
        })
    except Exception as e:
        return Response({
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def cart_recommendations(request):
    """Get recommendations based on current cart contents - this is the correct function name"""
    try:
        print("=" * 80)
        print("CART RECOMMENDATIONS API CALLED")
        print("=" * 80)
        
        # Get cart for current user/session
        from cart.views import get_or_create_cart
        cart = get_or_create_cart(request)
        cart_items = cart.items.select_related('product', 'product_variant').all()
        
        print(f"DEBUG api_views.py: Cart has {cart_items.count()} items")
        
        # Log each cart item's SKU
        for item in cart_items:
            if item.product_variant:
                print(f"DEBUG api_views.py: Cart item variant SKU: {item.product_variant.sku}")
            if item.product:
                print(f"DEBUG api_views.py: Cart item product SKU: {item.product.sku}")
        
        limit = request.data.get('limit', 4)
        print(f"DEBUG api_views.py: Requesting {limit} recommendations")
        
        # Get recommendations
        from .services import ProductRecommender
        recommended_products = ProductRecommender.get_cart_recommendations(cart_items, top_n=limit)
        
        print(f"DEBUG api_views.py: Got {len(recommended_products)} recommendations")
        for prod in recommended_products:
            print(f"  - {prod.name} (SKU: {prod.sku})")
        
        # Serialize products
        from products.serializers import ProductSerializer
        serializer = ProductSerializer(recommended_products, many=True, context={'request': request})
        
        print(f"DEBUG api_views.py: Returning {len(serializer.data)} serialized products")
        print("=" * 80)
        
        return Response({
            'success': True,
            'recommendations': serializer.data,
            'count': len(recommended_products)
        })
        
    except Exception as e:
        print(f"DEBUG api_views.py ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        print("=" * 80)
        return Response({
            'success': False,
            'error': str(e),
            'recommendations': []
        }, status=500)
