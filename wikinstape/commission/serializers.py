from rest_framework import serializers
from .models import *
from users.models import User
from services.models import ServiceCategory, ServiceSubCategory

class CommissionPlanSerializer(serializers.ModelSerializer):
    assigned_users_count = serializers.SerializerMethodField()
    
    class Meta:
        model = CommissionPlan
        fields = [
            'id', 'name', 'plan_type', 'description', 'is_active',
            'assigned_users_count', 'created_at', 'updated_at'
        ]
    
    def get_assigned_users_count(self, obj):
        return UserCommissionPlan.objects.filter(commission_plan=obj, is_active=True).count()

class ServiceCommissionSerializer(serializers.ModelSerializer):
    service_category_name = serializers.CharField(source='service_category.name', read_only=True)
    service_subcategory_name = serializers.CharField(source='service_subcategory.name', read_only=True)
    commission_plan_name = serializers.CharField(source='commission_plan.name', read_only=True)
    
    class Meta:
        model = ServiceCommission
        fields = [
            'id', 'service_category', 'service_category_name', 'service_subcategory', 
            'service_subcategory_name', 'commission_plan', 'commission_plan_name',
            'commission_type', 'commission_value', 'admin_commission', 'master_commission',
            'dealer_commission', 'retailer_commission', 'min_amount', 'max_amount',
            'is_active', 'created_at', 'updated_at'
        ]
    
    def validate(self, data):
        """Validate commission distribution totals 100% for percentage type"""
        if data.get('commission_type') == 'percentage':
            total_commission = (
                data.get('admin_commission', 0) +
                data.get('master_commission', 0) +
                data.get('dealer_commission', 0) +
                data.get('retailer_commission', 0)
            )
            if total_commission != 100:
                raise serializers.ValidationError(
                    "Total commission distribution must equal 100% for percentage type commissions"
                )
        return data

class CommissionTransactionSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source='user.username', read_only=True)
    retailer_username = serializers.CharField(source='retailer_user.username', read_only=True)
    service_name = serializers.SerializerMethodField()
    transaction_reference = serializers.CharField(source='main_transaction.reference_number', read_only=True)
    
    class Meta:
        model = CommissionTransaction
        fields = [
            'id', 'reference_number', 'user', 'user_username', 'role', 
            'commission_amount', 'retailer_user', 'retailer_username',
            'original_transaction_amount', 'main_transaction', 'transaction_reference',
            'service_submission', 'service_name', 'commission_config', 'commission_plan',
            'transaction_type', 'status', 'description', 'created_at'
        ]
    
    def get_service_name(self, obj):
        if obj.service_submission:
            return obj.service_submission.service_form.name
        return "N/A"

class UserCommissionPlanSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source='user.username', read_only=True)
    user_role = serializers.CharField(source='user.role', read_only=True)
    commission_plan_name = serializers.CharField(source='commission_plan.name', read_only=True)
    commission_plan_type = serializers.CharField(source='commission_plan.plan_type', read_only=True)
    assigned_by_username = serializers.CharField(source='assigned_by.username', read_only=True)
    
    class Meta:
        model = UserCommissionPlan
        fields = [
            'id', 'user', 'user_username', 'user_role', 'commission_plan', 
            'commission_plan_name', 'commission_plan_type', 'is_active',
            'assigned_by', 'assigned_by_username', 'assigned_at', 'updated_at'
        ]

class CommissionPayoutSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source='user.username', read_only=True)
    user_role = serializers.CharField(source='user.role', read_only=True)
    processed_by_username = serializers.CharField(source='processed_by.username', read_only=True)
    
    class Meta:
        model = CommissionPayout
        fields = [
            'id', 'user', 'user_username', 'user_role', 'total_amount',
            'commission_period_start', 'commission_period_end', 'status',
            'reference_number', 'payout_method', 'payout_reference',
            'processed_by', 'processed_by_username', 'processed_at',
            'created_at', 'updated_at'
        ]

class CommissionStatsSerializer(serializers.Serializer):
    total_commission = serializers.DecimalField(max_digits=15, decimal_places=2)
    pending_payouts = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_payouts = serializers.DecimalField(max_digits=15, decimal_places=2)
    commission_by_role = serializers.DictField()
    top_services = serializers.ListField()

class AssignCommissionPlanSerializer(serializers.Serializer):
    user_ids = serializers.ListField(child=serializers.IntegerField())
    commission_plan_id = serializers.IntegerField()

class CommissionCalculatorSerializer(serializers.Serializer):
    service_subcategory_id = serializers.IntegerField()
    transaction_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    user_id = serializers.IntegerField(required=False)