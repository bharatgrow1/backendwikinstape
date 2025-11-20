# services/managers.py
from django.db import models

class ServiceManager(models.Manager):
    def get_available_categories(self, user):
        """Get categories available for user - IMPROVED VERSION"""
        from .models import ServiceCategory, RoleServicePermission, UserServicePermission
        
        all_categories = ServiceCategory.objects.filter(is_active=True)
        available_categories = []
        
        for category in all_categories:
            # Skip if category itself is inactive
            if not category.is_active:
                continue
                
            # Check user-specific permissions first
            user_perm = UserServicePermission.objects.filter(
                user=user,
                service_category=category,
                is_active=True
            ).first()
            
            if user_perm:
                if user_perm.can_view and user_perm.can_use:
                    available_categories.append(category)
                continue
            
            # Check role permissions
            role_perm = RoleServicePermission.objects.filter(
                role=user.role,
                service_category=category,
                is_active=True
            ).first()
            
            if role_perm:
                if role_perm.can_view and role_perm.can_use:
                    available_categories.append(category)
            else:
                # No explicit permission = allow by default
                available_categories.append(category)
        
        return available_categories
    
    def get_available_subcategories(self, user, category=None):
        """Get subcategories available for user - IMPROVED VERSION"""
        from .models import ServiceSubCategory, RoleServicePermission, UserServicePermission
        
        # Base queryset - ONLY active subcategories
        subcategories = ServiceSubCategory.objects.filter(is_active=True)
        
        if category:
            subcategories = subcategories.filter(category=category)
        
        available_subcategories = []
        
        for subcategory in subcategories:
            # Double check subcategory is active
            if not subcategory.is_active:
                continue
                
            # First check if parent category is accessible AND active
            parent_category = subcategory.category
            if not parent_category.is_active:
                continue
                
            parent_accessible = self.can_access_service(user, service_category=parent_category)
            
            if not parent_accessible:
                continue  # Skip if parent category is not accessible
            
            # Check user-specific permissions for subcategory
            user_perm = UserServicePermission.objects.filter(
                user=user,
                service_subcategory=subcategory,
                is_active=True
            ).first()
            
            if user_perm:
                if user_perm.can_view and user_perm.can_use:
                    available_subcategories.append(subcategory)
                continue
            
            # Check role permissions for subcategory
            role_perm = RoleServicePermission.objects.filter(
                role=user.role,
                service_subcategory=subcategory,
                is_active=True
            ).first()
            
            if role_perm:
                if role_perm.can_view and role_perm.can_use:
                    available_subcategories.append(subcategory)
            else:
                # No explicit permission = allow by default
                available_subcategories.append(subcategory)
        
        return available_subcategories
    
    def can_access_service(self, user, service_category=None, service_subcategory=None):
        """Check if user can access specific service - FIXED VERSION"""
        from .models import RoleServicePermission, UserServicePermission
        
        if service_category:
            # Check user-specific permissions first
            user_perm = UserServicePermission.objects.filter(
                user=user,
                service_category=service_category,
                is_active=True
            ).first()
            
            if user_perm:
                return user_perm.can_view and user_perm.can_use
            
            # Check role permissions
            role_perm = RoleServicePermission.objects.filter(
                role=user.role,
                service_category=service_category,
                is_active=True
            ).first()
            
            if role_perm:
                return role_perm.can_view and role_perm.can_use
            else:
                # No explicit permission = allow by default
                return True
                
        elif service_subcategory:
            # First check parent category access
            parent_access = self.can_access_service(user, service_category=service_subcategory.category)
            if not parent_access:
                return False
            
            # Check user-specific permissions
            user_perm = UserServicePermission.objects.filter(
                user=user,
                service_subcategory=service_subcategory,
                is_active=True
            ).first()
            
            if user_perm:
                return user_perm.can_view and user_perm.can_use
            
            # Check role permissions
            role_perm = RoleServicePermission.objects.filter(
                role=user.role,
                service_subcategory=service_subcategory,
                is_active=True
            ).first()
            
            if role_perm:
                return role_perm.can_view and role_perm.can_use
            else:
                # No explicit permission = allow by default
                return True
        
        return False