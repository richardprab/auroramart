from rest_framework import viewsets, generics, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticatedOrReadOnly, IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q
from .models import Category, Product, ProductVariant, Review
from .serializers import (
    CategorySerializer,
    ProductListSerializer,
    ProductDetailSerializer,
    ProductVariantSerializer,
    ReviewSerializer,
    RelatedProductSerializer
)


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing categories.
    List and retrieve only (read-only).
    """
    queryset = Category.objects.filter(is_active=True)
    serializer_class = CategorySerializer
    lookup_field = 'slug'
    
    @action(detail=True, methods=['get'])
    def products(self, request, slug=None):
        """Get all products in this category"""
        category = self.get_object()
        products = Product.objects.filter(
            category=category,
            is_active=True
        )
        serializer = ProductListSerializer(products, many=True, context={'request': request})
        return Response(serializer.data)


class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing products.
    List and retrieve with filtering, searching, and ordering.
    """
    queryset = Product.objects.filter(is_active=True).select_related('category').prefetch_related('images', 'variants')
    permission_classes = [IsAuthenticatedOrReadOnly]
    lookup_field = 'slug'
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['category', 'is_featured', 'brand']
    search_fields = ['name', 'description', 'sku', 'brand']
    ordering_fields = ['created_at', 'rating', 'name']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return ProductDetailSerializer
        return ProductListSerializer
    
    @action(detail=True, methods=['get'])
    def variants(self, request, slug=None):
        """Get all variants for this product"""
        product = self.get_object()
        variants = product.variants.filter(is_active=True)
        serializer = ProductVariantSerializer(variants, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def reviews(self, request, slug=None):
        """Get all reviews for this product"""
        product = self.get_object()
        reviews = product.reviews.all()
        serializer = ReviewSerializer(reviews, many=True, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def related(self, request, slug=None):
        """Get related products (complementary and alternatives)"""
        product = self.get_object()
        related = product.related_from.select_related('to_product')
        serializer = RelatedProductSerializer(related, many=True, context={'request': request})
        return Response(serializer.data)


class ProductVariantViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing product variants.
    """
    queryset = ProductVariant.objects.filter(is_active=True)
    serializer_class = ProductVariantSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]


class ReviewViewSet(viewsets.ModelViewSet):
    """
    ViewSet for product reviews.
    Users can create, read, update their own reviews.
    """
    queryset = Review.objects.all()
    serializer_class = ReviewSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        product_id = self.request.query_params.get('product_id', None)
        if product_id:
            queryset = queryset.filter(product_id=product_id)
        return queryset
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    
    def get_permissions(self):
        if self.action in ['update', 'partial_update', 'destroy']:
            return [IsAuthenticated()]
        return super().get_permissions()
    
    def update(self, request, *args, **kwargs):
        review = self.get_object()
        if review.user != request.user:
            return Response(
                {'detail': 'You can only edit your own reviews.'},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().update(request, *args, **kwargs)
    
    def destroy(self, request, *args, **kwargs):
        review = self.get_object()
        if review.user != request.user:
            return Response(
                {'detail': 'You can only delete your own reviews.'},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().destroy(request, *args, **kwargs)
