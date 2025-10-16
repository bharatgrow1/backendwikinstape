from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import ServiceCategory, ServiceSubCategory
from .serializers import ServiceCategorySerializer, ServiceSubCategorySerializer

class ServiceCategoryViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = ServiceCategory.objects.all()
    serializer_class = ServiceCategorySerializer

    def get_queryset(self):
        queryset = ServiceCategory.objects.all()
        # Only show active categories to non-admin users
        if not self.request.user.is_admin_user():
            queryset = queryset.filter(is_active=True)
        return queryset

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(created_by=self.request.user)

class ServiceSubCategoryViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = ServiceSubCategory.objects.all()
    serializer_class = ServiceSubCategorySerializer

    def get_queryset(self):
        queryset = ServiceSubCategory.objects.all()
        category_id = self.request.query_params.get('category_id')
        
        # Filter by category if provided
        if category_id:
            queryset = queryset.filter(category_id=category_id)
        
        # Only show active subcategories to non-admin users
        if not self.request.user.is_admin_user():
            queryset = queryset.filter(is_active=True, category__is_active=True)
            
        return queryset

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=False, methods=['get'])
    def by_category(self, request):
        """Get subcategories by category ID"""
        category_id = request.query_params.get('category_id')
        if not category_id:
            return Response(
                {'error': 'category_id parameter is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        subcategories = ServiceSubCategory.objects.filter(category_id=category_id, is_active=True)
        serializer = self.get_serializer(subcategories, many=True)
        return Response(serializer.data)