from django.db import models

class ServiceManager(models.Manager):
    def get_services_for_user(self, user):
        """Get services available for specific user"""
        from .models import RoleServicePermission, UserServicePermission
        
        # First get user-specific permissions
        user_permissions = UserServicePermission.objects.filter(
            user=user, 
            is_active=True
        ).select_related('service_category', 'service_subcategory')
        
        # Then get role permissions
        role_permissions = RoleServicePermission.objects.filter(
            role=user.role,
            is_active=True
        ).select_related('service_category', 'service_subcategory')
        
        return {
            'user_permissions': user_permissions,
            'role_permissions': role_permissions
        }
    
    def get_available_categories(self, user):
        """Get categories available for user"""
        from .models import ServiceCategory
        
        all_categories = ServiceCategory.objects.filter(is_active=True)
        available_categories = []
        
        for category in all_categories:
            if self.can_access_service(user, service_category=category):
                available_categories.append(category)
        
        return available_categories
    
    def get_available_subcategories(self, user, category=None):
        """Get subcategories available for user"""
        from .models import ServiceSubCategory
        
        if category:
            subcategories = ServiceSubCategory.objects.filter(
                category=category, 
                is_active=True
            )
        else:
            subcategories = ServiceSubCategory.objects.filter(is_active=True)
        
        available_subcategories = []
        
        for subcategory in subcategories:
            if self.can_access_service(user, service_subcategory=subcategory):
                available_subcategories.append(subcategory)
        
        return available_subcategories
    
    def can_access_service(self, user, service_category=None, service_subcategory=None):
        """Check if user can access specific service"""
        from .models import RoleServicePermission, UserServicePermission
        
        # Check user-specific permissions first
        if service_category:
            user_perm = UserServicePermission.objects.filter(
                user=user,
                service_category=service_category,
                is_active=True
            ).first()
            
            role_perm = RoleServicePermission.objects.filter(
                role=user.role,
                service_category=service_category,
                is_active=True
            ).first()
        elif service_subcategory:
            user_perm = UserServicePermission.objects.filter(
                user=user,
                service_subcategory=service_subcategory,
                is_active=True
            ).first()
            
            role_perm = RoleServicePermission.objects.filter(
                role=user.role,
                service_subcategory=service_subcategory,
                is_active=True
            ).first()
        else:
            return False
        
        # User permission overrides role permission
        if user_perm:
            return user_perm.can_view and user_perm.can_use
        
        # Fallback to role permission
        if role_perm:
            return role_perm.can_view and role_perm.can_use
        
        # Default: no access if no permission set
        return False