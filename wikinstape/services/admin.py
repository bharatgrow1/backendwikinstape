from django.contrib import admin
from .models import RoleServicePermission, UserServicePermission

@admin.register(RoleServicePermission)
class RoleServicePermissionAdmin(admin.ModelAdmin):
    list_display = ['role', 'service_category', 'service_subcategory', 'is_active', 'can_view', 'can_use']
    list_filter = ['role', 'is_active']
    search_fields = ['role', 'service_category__name', 'service_subcategory__name']

@admin.register(UserServicePermission)
class UserServicePermissionAdmin(admin.ModelAdmin):
    list_display = ['user', 'service_category', 'service_subcategory', 'is_active', 'can_view', 'can_use']
    list_filter = ['user__role', 'is_active']
    search_fields = ['user__username', 'service_category__name', 'service_subcategory__name']