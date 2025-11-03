from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from decimal import Decimal
from .models import Order, OrderItem
from .serializers import OrderSerializer, OrderCreateSerializer
from cart.api_views import get_or_create_cart
from accounts.models import Address


class OrderViewSet(viewsets.ModelViewSet):
    """ViewSet for orders"""
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).prefetch_related('items')
    
    def get_serializer_class(self):
        if self.action == 'create':
            return OrderCreateSerializer
        return OrderSerializer
    
    def create(self, request, *args, **kwargs):
        """Create order from cart"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Get cart
        cart = get_or_create_cart(request)
        if not cart.items.exists():
            return Response(
                {'error': 'Cart is empty'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get address
        address_id = serializer.validated_data['address_id']
        address = Address.objects.get(id=address_id, user=request.user)
        
        # Calculate totals
        subtotal = cart.get_total()
        tax = (subtotal * Decimal('0.10')).quantize(Decimal('0.01'))
        shipping_cost = Decimal('10.00')
        total = (subtotal + tax + shipping_cost).quantize(Decimal('0.01'))
        
        # Create order
        order = Order.objects.create(
            user=request.user,
            address=address,
            subtotal=subtotal,
            tax=tax,
            shipping_cost=shipping_cost,
            total=total,
            total_amount=total,
            payment_method=serializer.validated_data['payment_method'],
            contact_number=serializer.validated_data['contact_number'],
            customer_notes=serializer.validated_data.get('customer_notes', ''),
            delivery_address=f"{address.address_line1}, {address.city}, {address.state} {address.zip_code}",
            status='pending'
        )
        
        # Create order items from cart
        for cart_item in cart.items.all():
            OrderItem.objects.create(
                order=order,
                product=cart_item.product,
                product_variant=cart_item.product_variant,
                quantity=cart_item.quantity,
                price=cart_item.product_variant.price
            )
        
        # Clear cart
        cart.clear()
        
        # Return order
        order_serializer = OrderSerializer(order, context={'request': request})
        return Response(order_serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel an order"""
        order = self.get_object()
        
        if order.status not in ['pending', 'confirmed']:
            return Response(
                {'error': 'Order cannot be cancelled in current status'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        order.status = 'cancelled'
        order.save()
        
        return Response({
            'success': True,
            'message': 'Order cancelled successfully'
        })
