from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Address, Wishlist, SaleSubscription, BrowsingHistory, ChatConversation, ChatMessage
from products.serializers import ProductListSerializer, ProductVariantSerializer

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model"""
    full_name = serializers.CharField(source='get_full_name', read_only=True)
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name', 'full_name',
            'phone', 'date_of_birth', 'avatar', 'role', 'age_range', 'gender',
            'employment', 'income_range', 'preferred_category',
            'allow_marketing_emails', 'allow_sale_notifications',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'username', 'created_at', 'updated_at']
        extra_kwargs = {
            'password': {'write_only': True}
        }


class UserRegistrationSerializer(serializers.ModelSerializer):
    """Serializer for user registration"""
    password = serializers.CharField(write_only=True, min_length=8, style={'input_type': 'password'})
    password_confirm = serializers.CharField(write_only=True, min_length=8, style={'input_type': 'password'})
    
    class Meta:
        model = User
        fields = [
            'username', 'email', 'password', 'password_confirm',
            'first_name', 'last_name', 'phone'
        ]
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({"password": "Passwords do not match."})
        return attrs
    
    def create(self, validated_data):
        validated_data.pop('password_confirm')
        user = User.objects.create_user(**validated_data)
        return user


class AddressSerializer(serializers.ModelSerializer):
    """Serializer for Address model"""
    
    class Meta:
        model = Address
        fields = [
            'id', 'user', 'full_name', 'address_type', 'address_line1',
            'address_line2', 'city', 'state', 'postal_code', 'zip_code',
            'country', 'is_default', 'created_at'
        ]
        read_only_fields = ['id', 'user', 'created_at']


class WishlistSerializer(serializers.ModelSerializer):
    """Serializer for Wishlist model"""
    product = ProductListSerializer(read_only=True)
    product_variant = ProductVariantSerializer(read_only=True)
    product_id = serializers.IntegerField(write_only=True, required=False)
    product_variant_id = serializers.IntegerField(write_only=True, required=False)
    
    class Meta:
        model = Wishlist
        fields = [
            'id', 'user', 'product', 'product_variant',
            'product_id', 'product_variant_id', 'added_at', 'created_at'
        ]
        read_only_fields = ['id', 'user', 'added_at', 'created_at']
    
    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class SaleSubscriptionSerializer(serializers.ModelSerializer):
    """Serializer for SaleSubscription model"""
    product_variant = ProductVariantSerializer(read_only=True)
    product_variant_id = serializers.IntegerField(write_only=True)
    
    class Meta:
        model = SaleSubscription
        fields = [
            'id', 'user', 'product_variant', 'product_variant_id',
            'category', 'is_active', 'subscribed_at', 'created_at'
        ]
        read_only_fields = ['id', 'user', 'subscribed_at', 'created_at']
    
    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class BrowsingHistorySerializer(serializers.ModelSerializer):
    """Serializer for BrowsingHistory model"""
    product = ProductListSerializer(read_only=True)
    product_id = serializers.IntegerField(write_only=True)
    
    class Meta:
        model = BrowsingHistory
        fields = ['id', 'user', 'product', 'product_id', 'viewed_at']
        read_only_fields = ['id', 'user', 'viewed_at']
    
    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class ChatMessageSerializer(serializers.ModelSerializer):
    """Serializer for ChatMessage model"""
    sender_name = serializers.CharField(source='sender.get_full_name', read_only=True)
    
    class Meta:
        model = ChatMessage
        fields = ['id', 'conversation', 'sender', 'sender_name', 'content', 'created_at']
        read_only_fields = ['id', 'sender', 'created_at']


class ChatConversationSerializer(serializers.ModelSerializer):
    """Serializer for ChatConversation model"""
    messages = ChatMessageSerializer(many=True, read_only=True)
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    admin_name = serializers.CharField(source='admin.get_full_name', read_only=True)
    product = ProductListSerializer(read_only=True)
    
    class Meta:
        model = ChatConversation
        fields = [
            'id', 'user', 'user_name', 'product', 'admin', 'admin_name',
            'subject', 'message_type', 'status', 'user_has_unread',
            'admin_has_unread', 'messages', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']
