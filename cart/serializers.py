from rest_framework import serializers
from .models import Cart, CartItem
from products.serializers import ProductListSerializer, ProductVariantSerializer
from decimal import Decimal


class CartItemSerializer(serializers.ModelSerializer):
    """Serializer for CartItem model"""
    product = ProductListSerializer(read_only=True)
    product_variant = ProductVariantSerializer(read_only=True)
    product_id = serializers.IntegerField(write_only=True, required=False)
    product_variant_id = serializers.IntegerField(write_only=True)
    subtotal = serializers.SerializerMethodField()
    
    class Meta:
        model = CartItem
        fields = [
            'id', 'cart', 'product', 'product_variant',
            'product_id', 'product_variant_id', 'quantity',
            'subtotal', 'added_at'
        ]
        read_only_fields = ['id', 'cart', 'added_at']
    
    def get_subtotal(self, obj):
        return str(obj.get_subtotal())
    
    def validate_quantity(self, value):
        if value < 1:
            raise serializers.ValidationError("Quantity must be at least 1.")
        return value
    
    def validate(self, attrs):
        # Check stock availability
        variant_id = attrs.get('product_variant_id')
        quantity = attrs.get('quantity', 1)
        
        if variant_id:
            from products.models import ProductVariant
            try:
                variant = ProductVariant.objects.get(id=variant_id)
                if variant.stock < quantity:
                    raise serializers.ValidationError({
                        'quantity': f'Only {variant.stock} items available in stock.'
                    })
            except ProductVariant.DoesNotExist:
                raise serializers.ValidationError({
                    'product_variant_id': 'Product variant does not exist.'
                })
        
        return attrs


class CartSerializer(serializers.ModelSerializer):
    """Serializer for Cart model"""
    items = CartItemSerializer(many=True, read_only=True)
    total = serializers.SerializerMethodField()
    item_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Cart
        fields = [
            'id', 'user', 'session_key', 'items',
            'total', 'item_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'user', 'session_key', 'created_at', 'updated_at']
    
    def get_total(self, obj):
        return str(obj.get_total())
    
    def get_item_count(self, obj):
        return obj.get_item_count()


class AddToCartSerializer(serializers.Serializer):
    """Serializer for adding items to cart"""
    product_id = serializers.IntegerField(required=False)
    product_variant_id = serializers.IntegerField()
    quantity = serializers.IntegerField(default=1, min_value=1)
    
    def validate_quantity(self, value):
        if value < 1:
            raise serializers.ValidationError("Quantity must be at least 1.")
        return value
    
    def validate(self, attrs):
        # Check if variant exists and has stock
        variant_id = attrs.get('product_variant_id')
        quantity = attrs.get('quantity', 1)
        
        from products.models import ProductVariant
        try:
            variant = ProductVariant.objects.get(id=variant_id)
            if variant.stock < quantity:
                raise serializers.ValidationError(
                    f'Only {variant.stock} items available in stock.'
                )
            attrs['variant'] = variant
        except ProductVariant.DoesNotExist:
            raise serializers.ValidationError('Product variant does not exist.')
        
        return attrs


class UpdateCartItemSerializer(serializers.Serializer):
    """Serializer for updating cart item quantity"""
    quantity = serializers.IntegerField(min_value=1)
    
    def validate_quantity(self, value):
        if value < 1:
            raise serializers.ValidationError("Quantity must be at least 1.")
        return value
