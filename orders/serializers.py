from rest_framework import serializers
from .models import Order, OrderItem
from products.serializers import ProductVariantSerializer
from accounts.serializers import AddressSerializer


class OrderItemSerializer(serializers.ModelSerializer):
    """Serializer for OrderItem model"""
    product_variant = ProductVariantSerializer(read_only=True)
    product_variant_id = serializers.IntegerField(write_only=True, required=False)
    subtotal = serializers.ReadOnlyField()
    
    class Meta:
        model = OrderItem
        fields = [
            'id', 'order', 'product', 'product_variant',
            'product_variant_id', 'quantity', 'price', 'subtotal'
        ]
        read_only_fields = ['id', 'order', 'price']


class OrderSerializer(serializers.ModelSerializer):
    """Serializer for Order model"""
    items = OrderItemSerializer(many=True, read_only=True)
    address = AddressSerializer(read_only=True)
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    
    class Meta:
        model = Order
        fields = [
            'id', 'order_number', 'user', 'user_name', 'address',
            'subtotal', 'tax', 'shipping_cost', 'total', 'status',
            'payment_method', 'payment_status', 'current_location',
            'tracking_number', 'expected_delivery_date', 'contact_number',
            'delivery_address', 'customer_notes', 'admin_notes',
            'items', 'created_at', 'updated_at', 'paid_at',
            'shipped_at', 'delivered_at'
        ]
        read_only_fields = [
            'id', 'order_number', 'user', 'created_at', 'updated_at',
            'paid_at', 'shipped_at', 'delivered_at'
        ]


class OrderCreateSerializer(serializers.Serializer):
    """Serializer for creating orders from cart"""
    address_id = serializers.IntegerField()
    payment_method = serializers.CharField(max_length=50)
    contact_number = serializers.CharField(max_length=20)
    customer_notes = serializers.CharField(required=False, allow_blank=True)
    
    def validate_address_id(self, value):
        from accounts.models import Address
        user = self.context['request'].user
        try:
            address = Address.objects.get(id=value, user=user)
        except Address.DoesNotExist:
            raise serializers.ValidationError("Address not found or does not belong to you.")
        return value
