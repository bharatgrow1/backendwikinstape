from rest_framework import serializers
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from .models import User, Wallet, Transaction, BalanceRequest, RolePermission

class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField()

class OTPVerifySerializer(serializers.Serializer):
    username = serializers.CharField()
    otp = serializers.CharField(max_length=6)

class WalletSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = Wallet
        fields = ['id', 'user', 'username', 'balance', 'created_at', 'updated_at']
        read_only_fields = ['balance', 'created_at', 'updated_at']

class TransactionSerializer(serializers.ModelSerializer):
    wallet_user = serializers.CharField(source='wallet.user.username', read_only=True)
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)

    class Meta:
        model = Transaction
        fields = ['id', 'wallet', 'wallet_user', 'amount', 'transaction_type', 
                 'description', 'created_by', 'created_by_username', 'created_at']
        read_only_fields = ['created_at']

class BalanceRequestCreateSerializer(serializers.ModelSerializer):
    retailer_username = serializers.CharField(source='retailer.username', read_only=True)

    class Meta:
        model = BalanceRequest
        fields = ['id', 'retailer', 'retailer_username', 'amount', 'description', 'status', 'created_at']
        read_only_fields = ['status', 'created_at']

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Amount must be greater than zero")
        return value

class BalanceRequestUpdateSerializer(serializers.ModelSerializer):
    retailer_username = serializers.CharField(source='retailer.username', read_only=True)
    processed_by_username = serializers.CharField(source='processed_by.username', read_only=True)

    class Meta:
        model = BalanceRequest
        fields = ['id', 'retailer', 'retailer_username', 'amount', 'status', 
                 'description', 'admin_notes', 'processed_by', 'processed_by_username', 
                 'created_at', 'updated_at']
        read_only_fields = ['retailer', 'amount', 'description', 'created_at', 'updated_at']

class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True)
    wallet = WalletSerializer(read_only=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'password', 'role', 'wallet']

    def create(self, validated_data):
        user = User(
            username=validated_data['username'],
            email=validated_data['email'],
            role=validated_data.get('role', 'retailer')
        )
        user.set_password(validated_data['password'])
        user.save()
        Wallet.objects.create(user=user)
        return user

class PermissionSerializer(serializers.ModelSerializer):
    content_type_name = serializers.CharField(source='content_type.model', read_only=True)
    app_label = serializers.CharField(source='content_type.app_label', read_only=True)
    
    class Meta:
        model = Permission
        fields = ['id', 'name', 'codename', 'content_type', 'content_type_name', 'app_label']

class UserPermissionSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    permission_ids = serializers.ListField(child=serializers.IntegerField())

class UserPermissionsSerializer(serializers.ModelSerializer):
    user_permissions = PermissionSerializer(many=True, read_only=True)
    model_permissions = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'username', 'role', 'user_permissions', 'model_permissions']
    
    def get_model_permissions(self, obj):
        """Get permissions grouped by model"""
        from django.apps import apps
        models_list = []
        
        for model in apps.get_models():
            if model._meta.app_label in ['auth', 'contenttypes', 'sessions']:
                continue
                
            permissions = obj.get_model_permissions(model)
            if any(permissions.values()):
                models_list.append({
                    'model': model._meta.model_name,
                    'app_label': model._meta.app_label,
                    'verbose_name': model._meta.verbose_name,
                    'permissions': permissions
                })
        
        return models_list

class ContentTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContentType
        fields = ['id', 'app_label', 'model']

class GrantRolePermissionSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=User.ROLE_CHOICES)
    permission_ids = serializers.ListField(child=serializers.IntegerField())

class ModelPermissionSerializer(serializers.Serializer):
    model = serializers.CharField()
    app_label = serializers.CharField()
    permissions = serializers.DictField()

class RolePermissionSerializer(serializers.ModelSerializer):
    permission_details = PermissionSerializer(source='permission', read_only=True)
    granted_by_username = serializers.CharField(source='granted_by.username', read_only=True)
    
    class Meta:
        model = RolePermission
        fields = ['id', 'role', 'permission', 'permission_details', 'granted_by', 'granted_by_username', 'created_at']