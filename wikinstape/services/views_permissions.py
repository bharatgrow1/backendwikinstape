from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.db import transaction

from .models import RoleServicePermission, UserServicePermission, ServiceCategory, ServiceSubCategory
from .serializers import (
    RoleServicePermissionSerializer, UserServicePermissionSerializer,
    BulkRolePermissionSerializer, BulkUserPermissionSerializer,
    AvailableServicesSerializer, ServiceCategorySerializer, ServiceSubCategorySerializer
)
from .views import CanManageServicePermissions

class ServicePermissionViewSet(viewsets.ViewSet):
    """Manage service permissions for roles and users"""
    permission_classes = [IsAuthenticated, CanManageServicePermissions]
    
    # Role Permissions Management
    
    @action(detail=False, methods=['get'])
    def role_permissions(self, request):
        """Get all role permissions"""
        role = request.query_params.get('role')
        
        if role:
            permissions = RoleServicePermission.objects.filter(role=role)
        else:
            permissions = RoleServicePermission.objects.all()
        
        serializer = RoleServicePermissionSerializer(permissions, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def create_role_permission(self, request):
        """Create role permission"""
        serializer = RoleServicePermissionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Check if permission already exists
        role = serializer.validated_data['role']
        service_category = serializer.validated_data.get('service_category')
        service_subcategory = serializer.validated_data.get('service_subcategory')
        
        existing_permission = RoleServicePermission.objects.filter(
            role=role,
            service_category=service_category,
            service_subcategory=service_subcategory
        ).first()
        
        if existing_permission:
            # Update existing permission
            update_serializer = RoleServicePermissionSerializer(
                existing_permission, 
                data=request.data, 
                partial=True
            )
            update_serializer.is_valid(raise_exception=True)
            update_serializer.save(created_by=request.user)
            return Response(update_serializer.data)
        
        serializer.save(created_by=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['put', 'patch'])
    def update_role_permission(self, request, pk=None):
        """Update role permission"""
        permission = get_object_or_404(RoleServicePermission, pk=pk)
        serializer = RoleServicePermissionSerializer(
            permission, 
            data=request.data, 
            partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def bulk_role_permissions(self, request):
        """Bulk update role permissions"""
        serializer = BulkRolePermissionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        role = serializer.validated_data['role']
        permissions_data = serializer.validated_data['permissions']
        
        created_count = 0
        updated_count = 0
        
        with transaction.atomic():
            for perm_data in permissions_data:
                service_category_id = perm_data.get('service_category_id')
                service_subcategory_id = perm_data.get('service_subcategory_id')
                
                # Validate that either category or subcategory is provided
                if not service_category_id and not service_subcategory_id:
                    continue
                
                # Find existing permission
                existing_perm = RoleServicePermission.objects.filter(
                    role=role,
                    service_category_id=service_category_id,
                    service_subcategory_id=service_subcategory_id
                ).first()
                
                if existing_perm:
                    # Update existing
                    for field in ['is_active', 'can_view', 'can_use']:
                        if field in perm_data:
                            setattr(existing_perm, field, perm_data[field])
                    existing_perm.save()
                    updated_count += 1
                else:
                    # Create new
                    RoleServicePermission.objects.create(
                        role=role,
                        service_category_id=service_category_id,
                        service_subcategory_id=service_subcategory_id,
                        is_active=perm_data.get('is_active', True),
                        can_view=perm_data.get('can_view', True),
                        can_use=perm_data.get('can_use', True),
                        created_by=request.user
                    )
                    created_count += 1
        
        return Response({
            'message': f'Created {created_count}, updated {updated_count} permissions',
            'role': role,
            'total_processed': len(permissions_data)
        })
    
    # User Permissions Management
    
    @action(detail=False, methods=['get'])
    def user_permissions(self, request):
        """Get user permissions"""
        user_id = request.query_params.get('user_id')
        
        if not user_id:
            return Response(
                {'error': 'user_id parameter is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user = get_object_or_404(User, id=user_id)
        permissions = UserServicePermission.objects.filter(user=user)
        
        serializer = UserServicePermissionSerializer(permissions, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def create_user_permission(self, request):
        """Create user permission"""
        serializer = UserServicePermissionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user_id = serializer.validated_data['user']
        service_category = serializer.validated_data.get('service_category')
        service_subcategory = serializer.validated_data.get('service_subcategory')
        
        # Check if user exists and dealer can manage this user
        user = get_object_or_404(User, id=user_id)
        if request.user.role == 'dealer' and user.created_by != request.user:
            return Response(
                {'error': 'You can only manage permissions for your retailers'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        existing_permission = UserServicePermission.objects.filter(
            user=user,
            service_category=service_category,
            service_subcategory=service_subcategory
        ).first()
        
        if existing_permission:
            update_serializer = UserServicePermissionSerializer(
                existing_permission, 
                data=request.data, 
                partial=True
            )
            update_serializer.is_valid(raise_exception=True)
            update_serializer.save(created_by=request.user)
            return Response(update_serializer.data)
        
        serializer.save(created_by=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['put', 'patch'])
    def update_user_permission(self, request, pk=None):
        """Update user permission"""
        permission = get_object_or_404(UserServicePermission, pk=pk)
        
        serializer = UserServicePermissionSerializer(
            permission, 
            data=request.data, 
            partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def bulk_user_permissions(self, request):
        """Bulk update user permissions"""
        serializer = BulkUserPermissionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user_id = serializer.validated_data['user_id']
        permissions_data = serializer.validated_data['permissions']
        
        user = get_object_or_404(User, id=user_id)
        
        # Check if dealer can manage this user
        if request.user.role == 'dealer' and user.created_by != request.user:
            return Response(
                {'error': 'You can only manage permissions for your retailers'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        created_count = 0
        updated_count = 0
        
        with transaction.atomic():
            for perm_data in permissions_data:
                service_category_id = perm_data.get('service_category_id')
                service_subcategory_id = perm_data.get('service_subcategory_id')
                
                if not service_category_id and not service_subcategory_id:
                    continue
                
                existing_perm = UserServicePermission.objects.filter(
                    user=user,
                    service_category_id=service_category_id,
                    service_subcategory_id=service_subcategory_id
                ).first()
                
                if existing_perm:
                    for field in ['is_active', 'can_view', 'can_use']:
                        if field in perm_data:
                            setattr(existing_perm, field, perm_data[field])
                    existing_perm.save()
                    updated_count += 1
                else:
                    UserServicePermission.objects.create(
                        user=user,
                        service_category_id=service_category_id,
                        service_subcategory_id=service_subcategory_id,
                        is_active=perm_data.get('is_active', True),
                        can_view=perm_data.get('can_view', True),
                        can_use=perm_data.get('can_use', True),
                        created_by=request.user
                    )
                    created_count += 1
        
        return Response({
            'message': f'Created {created_count}, updated {updated_count} permissions for {user.username}',
            'user_id': user_id,
            'total_processed': len(permissions_data)
        })
    
    # Available Services
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def my_services(self, request):
        """Get services available for current user"""
        user = request.user
        
        categories = ServiceCategory.objects.get_available_categories(user)
        subcategories = ServiceCategory.objects.get_available_subcategories(user)
        
        serializer = AvailableServicesSerializer({
            'categories': categories,
            'subcategories': subcategories
        })
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def available_services(self, request):
        """Get services available for specific user"""
        user_id = request.query_params.get('user_id')
        
        if user_id:
            user = get_object_or_404(User, id=user_id)
            # Check if current user can view this user's services
            if (request.user.role == 'dealer' and 
                user.created_by != request.user and 
                user.id != request.user.id):
                return Response(
                    {'error': 'You can only view services for your retailers'},
                    status=status.HTTP_403_FORBIDDEN
                )
        else:
            user = request.user
        
        categories = ServiceCategory.objects.get_available_categories(user)
        subcategories = ServiceCategory.objects.get_available_subcategories(user)
        
        # Get user's specific permissions
        user_permissions = UserServicePermission.objects.filter(user=user)
        role_permissions = RoleServicePermission.objects.filter(role=user.role)
        
        response_data = {
            'categories': ServiceCategorySerializer(categories, many=True).data,
            'subcategories': ServiceSubCategorySerializer(subcategories, many=True).data,
            'user_permissions': UserServicePermissionSerializer(user_permissions, many=True).data,
            'role_permissions': RoleServicePermissionSerializer(role_permissions, many=True).data,
            'user': {
                'id': user.id,
                'username': user.username,
                'role': user.role
            }
        }
        
        return Response(response_data)