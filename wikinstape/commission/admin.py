from django.contrib import admin
from .models import *

@admin.register(CommissionPlan)
class CommissionPlanAdmin(admin.ModelAdmin):
    list_display = ['name', 'plan_type', 'is_active', 'created_at']
    list_filter = ['plan_type', 'is_active']
    search_fields = ['name']

@admin.register(ServiceCommission)
class ServiceCommissionAdmin(admin.ModelAdmin):
    list_display = ['get_service_name', 'commission_plan', 'commission_type', 'commission_value', 'is_active']
    list_filter = ['commission_plan', 'commission_type', 'is_active']
    search_fields = ['service_category__name', 'service_subcategory__name']
    
    def get_service_name(self, obj):
        return obj.service_subcategory.name if obj.service_subcategory else obj.service_category.name
    get_service_name.short_description = 'Service'

@admin.register(CommissionTransaction)
class CommissionTransactionAdmin(admin.ModelAdmin):
    list_display = ['user', 'role', 'commission_amount', 'retailer_user', 'created_at']
    list_filter = ['role', 'status', 'created_at']
    readonly_fields = ['reference_number', 'created_at']

@admin.register(UserCommissionPlan)
class UserCommissionPlanAdmin(admin.ModelAdmin):
    list_display = ['user', 'commission_plan', 'is_active', 'assigned_at']
    list_filter = ['commission_plan', 'is_active']
    search_fields = ['user__username']