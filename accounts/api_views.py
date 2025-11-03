from rest_framework import viewsets, generics, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.views import TokenObtainPairView as BaseTokenObtainPairView
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


class TokenObtainPairView(BaseTokenObtainPairView):
    """
    Custom TokenObtainPairView that automatically merges session cart
    into user's cart after successful login.
    """
    def post(self, request, *args, **kwargs):
        # Get tokens using parent class
        response = super().post(request, *args, **kwargs)
        
        # If login successful and we have a session cart, merge it
        if response.status_code == 200 and request.session.session_key:
            try:
                from cart.views import merge_session_cart_to_user
                from django.contrib.auth import get_user_model
                
                User = get_user_model()
                # Get the user from the request (validated by JWT serializer)
                username = request.data.get('username')
                user = User.objects.filter(username=username).first()
                
                if user:
                    merge_result = merge_session_cart_to_user(user, request.session.session_key)
                    # Add merge info to response
                    response.data['cart_merged'] = {
                        'merged': merge_result['merged'],
                        'skipped': merge_result['skipped'],
                        'message': merge_result['message']
                    }
            except Exception as e:
                # Don't fail login if merge fails
                response.data['cart_merge_error'] = str(e)
        
        return response


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
