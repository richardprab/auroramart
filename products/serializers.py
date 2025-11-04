from rest_framework import serializers
from .models import (
    Category,
    Product,
    ProductImage,
    ProductVariant,
    Review,
    Attribute,
    AttributeValue,
    RelatedProduct,
)
from django.contrib.auth import get_user_model

User = get_user_model()


class CategorySerializer(serializers.ModelSerializer):
    """Serializer for Category model"""
    children = serializers.SerializerMethodField()
    
    class Meta:
        model = Category
        fields = [
            'id', 'name', 'slug', 'parent', 'description', 
            'image', 'is_active', 'children', 'created_at', 'updated_at'
        ]
        read_only_fields = ['slug', 'created_at', 'updated_at']
    
    def get_children(self, obj):
        if obj.children.exists():
            return CategorySerializer(obj.children.all(), many=True).data
        return []


class ProductImageSerializer(serializers.ModelSerializer):
    """Serializer for ProductImage model"""
    
    class Meta:
        model = ProductImage
        fields = ['id', 'image', 'alt_text', 'is_primary', 'display_order', 'created_at']
        read_only_fields = ['created_at']


class ProductVariantSerializer(serializers.ModelSerializer):
    """Serializer for ProductVariant model"""
    is_on_sale = serializers.ReadOnlyField()
    discount_percentage = serializers.ReadOnlyField()
    
    class Meta:
        model = ProductVariant
        fields = [
            'id', 'sku', 'color', 'size', 'material', 
            'price', 'compare_price', 'stock', 'weight',
            'is_active', 'is_default', 'is_on_sale', 
            'discount_percentage', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']


class ReviewSerializer(serializers.ModelSerializer):
    """Serializer for Review model"""
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    user_email = serializers.EmailField(source='user.email', read_only=True)
    
    class Meta:
        model = Review
        fields = [
            'id', 'product', 'user', 'user_name', 'user_email',
            'rating', 'title', 'comment', 'is_verified_purchase',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['user', 'is_verified_purchase', 'created_at', 'updated_at']
    
    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class ProductListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for product list views"""
    category_name = serializers.CharField(source='category.name', read_only=True)
    primary_image = serializers.SerializerMethodField()
    price_range = serializers.SerializerMethodField()
    lowest_variant = ProductVariantSerializer(source='get_lowest_priced_variant', read_only=True)
    
    class Meta:
        model = Product
        fields = [
            'id', 'name', 'slug', 'sku', 'category', 'category_name',
            'brand', 'rating', 'review_count', 'is_trending',
            'is_bestseller', 'is_featured', 'is_active',
            'primary_image', 'price_range', 'lowest_variant'
        ]
        read_only_fields = ['slug', 'rating', 'review_count']
    
    def get_primary_image(self, obj):
        image = obj.get_primary_image()
        if image:
            return {
                'id': image.id,
                'url': image.image.url if image.image else None,
                'alt_text': image.alt_text
            }
        return None
    
    def get_price_range(self, obj):
        min_price, max_price = obj.get_price_range()
        if min_price is not None:
            return {
                'min': str(min_price),
                'max': str(max_price)
            }
        return None


class ProductDetailSerializer(serializers.ModelSerializer):
    """Full serializer for product detail views"""
    category_name = serializers.CharField(source='category.name', read_only=True)
    images = ProductImageSerializer(many=True, read_only=True)
    variants = ProductVariantSerializer(many=True, read_only=True)
    reviews = ReviewSerializer(many=True, read_only=True)
    is_available = serializers.ReadOnlyField()
    price_range = serializers.SerializerMethodField()
    
    class Meta:
        model = Product
        fields = [
            'id', 'name', 'slug', 'sku', 'category', 'category_name',
            'description', 'size_guide', 'brand', 'rating', 'review_count',
            'is_trending', 'is_bestseller', 'is_featured', 'is_active',
            'is_available', 'images', 'variants', 'reviews', 'price_range',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['slug', 'rating', 'review_count', 'created_at', 'updated_at']
    
    def get_price_range(self, obj):
        min_price, max_price = obj.get_price_range()
        if min_price is not None:
            return {
                'min': str(min_price),
                'max': str(max_price)
            }
        return None


class RelatedProductSerializer(serializers.ModelSerializer):
    """Serializer for related products"""
    to_product = ProductListSerializer(read_only=True)
    
    class Meta:
        model = RelatedProduct
        fields = ['id', 'to_product', 'relation_type']
