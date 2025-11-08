from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
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
@permission_classes([IsAuthenticated])
def get_cart_recommendations(request):
    """Get product recommendations based on cart contents"""
    from cart.models import CartItem
    
    cart_items = CartItem.objects.filter(
        user=request.user
    ).select_related('variant__product')
    
    if not cart_items.exists():
        return Response({
            'recommendations': [],
            'message': 'Cart is empty'
        })
    
    top_n = int(request.POST.get('limit', 5))
    
    try:
        recommendations = ProductRecommender.get_cart_recommendations(cart_items, top_n=top_n)
        serializer = ProductListSerializer(recommendations, many=True, context={'request': request})
        
        return Response({
            'recommendations': serializer.data,
            'count': len(recommendations)
        })
    except Exception as e:
        return Response({
            'error': str(e)
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
