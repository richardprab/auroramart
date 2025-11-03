from rest_framework import viewsets, generics, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.contrib.auth import get_user_model
from .models import Address, Wishlist, SaleSubscription, BrowsingHistory, ChatConversation, ChatMessage
from .serializers import (
    UserSerializer,
    UserRegistrationSerializer,
    AddressSerializer,
    WishlistSerializer,
    SaleSubscriptionSerializer,
    BrowsingHistorySerializer,
    ChatConversationSerializer,
    ChatMessageSerializer
)

User = get_user_model()


# Removed TokenObtainPairView - using session authentication only
# JWT token endpoints removed as they're not needed for this app


class UserRegistrationView(generics.CreateAPIView):
    """API view for user registration"""
    queryset = User.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = [AllowAny]


class UserProfileView(generics.RetrieveUpdateAPIView):
    """API view for user profile"""
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        return self.request.user


class AddressViewSet(viewsets.ModelViewSet):
    """ViewSet for user addresses"""
    serializer_class = AddressSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Address.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class WishlistViewSet(viewsets.ModelViewSet):
    """ViewSet for user wishlist"""
    serializer_class = WishlistSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Wishlist.objects.filter(user=self.request.user).select_related('product', 'product_variant')
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    
    @action(detail=False, methods=['post'])
    def add_product(self, request):
        """Add a product to wishlist"""
        product_id = request.data.get('product_id')
        product_variant_id = request.data.get('product_variant_id')
        
        if not product_id and not product_variant_id:
            return Response(
                {'error': 'Either product_id or product_variant_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        wishlist_item, created = Wishlist.objects.get_or_create(
            user=request.user,
            product_id=product_id,
            product_variant_id=product_variant_id
        )
        
        if created:
            return Response({
                'success': True,
                'message': 'Added to wishlist'
            }, status=status.HTTP_201_CREATED)
        return Response({
            'success': False,
            'message': 'Already in wishlist'
        })
    
    @action(detail=False, methods=['delete'])
    def remove_product(self, request):
        """Remove a product from wishlist"""
        product_id = request.data.get('product_id')
        
        try:
            wishlist_item = Wishlist.objects.get(
                user=request.user,
                product_id=product_id
            )
            wishlist_item.delete()
            return Response({
                'success': True,
                'message': 'Removed from wishlist'
            })
        except Wishlist.DoesNotExist:
            return Response(
                {'success': False, 'message': 'Item not in wishlist'},
                status=status.HTTP_404_NOT_FOUND
            )


class SaleSubscriptionViewSet(viewsets.ModelViewSet):
    """ViewSet for sale subscriptions"""
    serializer_class = SaleSubscriptionSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return SaleSubscription.objects.filter(user=self.request.user)


class BrowsingHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for browsing history (read-only for users)"""
    serializer_class = BrowsingHistorySerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return BrowsingHistory.objects.filter(user=self.request.user)


class ChatConversationViewSet(viewsets.ModelViewSet):
    """ViewSet for chat conversations"""
    serializer_class = ChatConversationSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return ChatConversation.objects.filter(user=self.request.user)
    
    @action(detail=True, methods=['post'])
    def send_message(self, request, pk=None):
        """Send a message in a conversation"""
        conversation = self.get_object()
        content = request.data.get('content')
        
        if not content:
            return Response(
                {'error': 'Message content is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        message = ChatMessage.objects.create(
            conversation=conversation,
            sender=request.user,
            content=content
        )
        
        serializer = ChatMessageSerializer(message)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
