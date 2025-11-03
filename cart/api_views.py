from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Cart, CartItem
from .serializers import (
    CartSerializer,
    CartItemSerializer,
    AddToCartSerializer,
    UpdateCartItemSerializer
)
from products.models import Product, ProductVariant


def get_or_create_cart(request):
    """Helper function to get or create cart for user or session"""
    if request.user.is_authenticated:
        cart, created = Cart.objects.get_or_create(user=request.user)
    else:
        session_key = request.session.session_key
        if not session_key:
            request.session.create()
            session_key = request.session.session_key
        cart, created = Cart.objects.get_or_create(session_key=session_key)
    return cart


class CartViewSet(viewsets.ViewSet):
    """
    ViewSet for cart operations.
    Supports both authenticated and anonymous users.
    """
    permission_classes = []  # Allow anonymous access
    
    def list(self, request):
        """Get the current cart"""
        cart = get_or_create_cart(request)
        serializer = CartSerializer(cart, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def add_item(self, request):
        """Add item to cart"""
        serializer = AddToCartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        cart = get_or_create_cart(request)
        variant_id = serializer.validated_data['product_variant_id']
        quantity = serializer.validated_data['quantity']
        product_id = serializer.validated_data.get('product_id')
        
        variant = ProductVariant.objects.get(id=variant_id)
        product = variant.product if not product_id else Product.objects.get(id=product_id)
        
        # Check if item already exists
        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            product_variant=variant,
            defaults={'quantity': quantity, 'product': product}
        )
        
        if not created:
            # Update quantity
            new_quantity = cart_item.quantity + quantity
            if new_quantity > variant.stock:
                return Response(
                    {
                        'success': False,
                        'message': f'Only {variant.stock} items available.'
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            cart_item.quantity = new_quantity
            cart_item.save()
        
        return Response({
            'success': True,
            'message': f'{product.name} added to cart!',
            'cart_count': cart.get_item_count(),
            'cart': CartSerializer(cart, context={'request': request}).data
        })
    
    @action(detail=False, methods=['patch'])
    def update_item(self, request):
        """Update cart item quantity"""
        item_id = request.data.get('item_id')
        serializer = UpdateCartItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            cart = get_or_create_cart(request)
            cart_item = CartItem.objects.get(id=item_id, cart=cart)
            
            new_quantity = serializer.validated_data['quantity']
            if new_quantity > cart_item.product_variant.stock:
                return Response(
                    {
                        'success': False,
                        'message': f'Only {cart_item.product_variant.stock} items available.'
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            cart_item.quantity = new_quantity
            cart_item.save()
            
            return Response({
                'success': True,
                'message': 'Cart updated',
                'cart': CartSerializer(cart, context={'request': request}).data
            })
        except CartItem.DoesNotExist:
            return Response(
                {'success': False, 'message': 'Cart item not found'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=False, methods=['delete'])
    def remove_item(self, request):
        """Remove item from cart"""
        item_id = request.data.get('item_id')
        
        try:
            cart = get_or_create_cart(request)
            cart_item = CartItem.objects.get(id=item_id, cart=cart)
            cart_item.delete()
            
            return Response({
                'success': True,
                'message': 'Item removed from cart',
                'cart': CartSerializer(cart, context={'request': request}).data
            })
        except CartItem.DoesNotExist:
            return Response(
                {'success': False, 'message': 'Cart item not found'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=False, methods=['delete'])
    def clear(self, request):
        """Clear all items from cart"""
        cart = get_or_create_cart(request)
        cart.clear()
        
        return Response({
            'success': True,
            'message': 'Cart cleared',
            'cart': CartSerializer(cart, context={'request': request}).data
        })
    
    @action(detail=False, methods=['get'])
    def count(self, request):
        """Get cart item count"""
        cart = get_or_create_cart(request)
        return Response({'count': cart.get_item_count()})
    
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def merge(self, request):
        """
        Merge session cart into authenticated user's cart.
        Called after login to preserve guest cart items.
        """
        from .views import merge_session_cart_to_user
        
        session_key = request.session.session_key
        if not session_key:
            return Response({
                'success': False,
                'message': 'No session cart to merge'
            })
        
        # Perform merge
        result = merge_session_cart_to_user(request.user, session_key)
        
        # Get updated cart
        cart = get_or_create_cart(request)
        
        return Response({
            'success': True,
            'merged': result['merged'],
            'skipped': result['skipped'],
            'message': result['message'],
            'cart': CartSerializer(cart, context={'request': request}).data
        })
