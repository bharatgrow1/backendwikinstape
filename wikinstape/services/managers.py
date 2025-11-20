from django.db import models


class ServiceManager(models.Manager):
    def get_available_categories(self, user):
        """Get categories available for user"""
        from .models import ServiceCategory, RoleServicePermission, UserServicePermission
        
        all_categories = ServiceCategory.objects.filter(is_active=True)
        available_categories = []
        
        for category in all_categories:
            # Check user-specific permissions first
            user_perm = UserServicePermission.objects.filter(
                user=user,
                service_category=category,
                is_active=True
            ).first()
            
            if user_perm:
                if user_perm.can_view:
                    available_categories.append(category)
                continue
            
            # Check role permissions
            role_perm = RoleServicePermission.objects.filter(
                role=user.role,
                service_category=category,
                is_active=True
            ).first()
            
            if role_perm and role_perm.can_view:
                available_categories.append(category)
            # If no specific permission found, allow by default (for backward compatibility)
            elif not role_perm and not user_perm:
                available_categories.append(category)
        
        return available_categories
    
    def get_available_subcategories(self, user, category=None):
        """Get subcategories available for user - FIXED VERSION"""
        from .models import ServiceSubCategory, RoleServicePermission, UserServicePermission
        
        if category:
            subcategories = ServiceSubCategory.objects.filter(
                category=category, 
                is_active=True
            )
        else:
            subcategories = ServiceSubCategory.objects.filter(is_active=True)
        
        available_subcategories = []
        
        for subcategory in subcategories:
            # First check if the parent category is accessible
            parent_category_accessible = False
            
            # Check category permissions first
            category_user_perm = UserServicePermission.objects.filter(
                user=user,
                service_category=subcategory.category,
                is_active=True
            ).first()
            
            category_role_perm = RoleServicePermission.objects.filter(
                role=user.role,
                service_category=subcategory.category,
                is_active=True
            ).first()
            
            # Category is accessible if:
            # - User has explicit permission with can_view=True, OR
            # - Role has explicit permission with can_view=True, OR
            # - No explicit permission exists (default allow)
            if category_user_perm:
                parent_category_accessible = category_user_perm.can_view
            elif category_role_perm:
                parent_category_accessible = category_role_perm.can_view
            else:
                # No explicit permission = allow by default
                parent_category_accessible = True
            
            if not parent_category_accessible:
                continue  # Skip if parent category is not accessible
            
            # Now check subcategory-specific permissions
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
                # No explicit subcategory permission = allow if parent category is accessible
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
            
            # Check user-specific permissions first
            user_perm = UserServicePermission.objects.filter(
                user=user,
                service_subcategory=service_subcategory,
                is_active=True
            ).first()
            
            if user_perm:
                return user_perm.can_view and user_perm.can_use
            
            role_perm = RoleServicePermission.objects.filter(
                role=user.role,
                service_subcategory=service_subcategory,
                is_active=True
            ).first()
            
            if role_perm:
                return role_perm.can_view and role_perm.can_use
            else:
                return True
        
        return False