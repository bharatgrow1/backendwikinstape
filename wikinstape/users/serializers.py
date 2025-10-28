from rest_framework import serializers
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from .models import User, Wallet, Transaction, BalanceRequest, RolePermission, UserService, State, City
from services.models import ServiceSubCategory

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



class ServiceSubCategorySerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    
    class Meta:
        model = ServiceSubCategory
        fields = ['id', 'name', 'category_name', 'description', 'image', 'is_active']




class UserServiceSerializer(serializers.ModelSerializer):
    service_details = ServiceSubCategorySerializer(source='service', read_only=True)
    
    class Meta:
        model = UserService
        fields = ['id', 'service', 'service_details', 'is_active', 'created_at']



class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True)
    created_by_role = serializers.CharField(source='created_by.role', read_only=True)
    service_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False,
        allow_empty=True
    )

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'password', 'role', 'created_by', 'created_by_role',
            # Personal Information
            'first_name', 'last_name', 'phone_number', 'alternative_phone', 
            'aadhar_number', 'pan_number', 'date_of_birth', 'gender',
            # Business Information
            'business_name', 'business_nature', 'business_registration_number',
            'gst_number', 'business_ownership_type',
            # Address Information
            'address', 'city', 'state', 'pincode', 'landmark',
            # Bank Information
            'bank_name', 'account_number', 'ifsc_code', 'account_holder_name',
            # Services
            'service_ids'
        ]
        read_only_fields = ['created_by']

    def validate_role(self, value):
        request = self.context.get('request')
        if not request:
            raise serializers.ValidationError("Request context is required")
        
        current_user = request.user
        target_role = value
        
        role_hierarchy = {
            'superadmin': ['superadmin', 'admin', 'master', 'dealer', 'retailer'],
            'admin': ['admin', 'master', 'dealer', 'retailer'],
            'master': ['master', 'dealer', 'retailer'],
            'dealer': ['retailer'],
            'retailer': []
        }
        
        if current_user.role not in role_hierarchy:
            raise serializers.ValidationError("Invalid current user role")
        
        if target_role not in role_hierarchy[current_user.role]:
            raise serializers.ValidationError(f"You cannot create users with {target_role} role")
        
        return value

    def create(self, validated_data):
        service_ids = validated_data.pop('service_ids', [])
        
        user = User(
            username=validated_data['username'],
            email=validated_data.get('email', ''),
            role=validated_data['role'],
            created_by=self.context['request'].user,
            # Personal Information
            first_name=validated_data.get('first_name'),
            last_name=validated_data.get('last_name'),
            phone_number=validated_data.get('phone_number'),
            alternative_phone=validated_data.get('alternative_phone'),
            aadhar_number=validated_data.get('aadhar_number'),
            pan_number=validated_data.get('pan_number'),
            date_of_birth=validated_data.get('date_of_birth'),
            gender=validated_data.get('gender'),
            # Business Information
            business_name=validated_data.get('business_name'),
            business_nature=validated_data.get('business_nature'),
            business_registration_number=validated_data.get('business_registration_number'),
            gst_number=validated_data.get('gst_number'),
            business_ownership_type=validated_data.get('business_ownership_type'),
            # Address Information
            address=validated_data.get('address'),
            city=validated_data.get('city'),
            state=validated_data.get('state'),
            pincode=validated_data.get('pincode'),
            landmark=validated_data.get('landmark'),
            # Bank Information
            bank_name=validated_data.get('bank_name'),
            account_number=validated_data.get('account_number'),
            ifsc_code=validated_data.get('ifsc_code'),
            account_holder_name=validated_data.get('account_holder_name'),
        )
        user.set_password(validated_data['password'])
        user.save()
        
        # Create wallet
        Wallet.objects.create(user=user)
        
        try:
            for service_id in service_ids:
                try:
                    service = ServiceSubCategory.objects.get(id=service_id, is_active=True)
                    UserService.objects.create(user=user, service=service)
                except ServiceSubCategory.DoesNotExist:
                    continue
        except Exception as e:
            print(f"Service assignment failed: {e}")
        
        return user
    

class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False)
    wallet = WalletSerializer(read_only=True)
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    services = UserServiceSerializer(many=True, read_only=True, source='user_services')

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'password', 'role', 'wallet', 'created_by', 
            'created_by_username', 'date_joined', 'services',
            # Personal Information
            'first_name', 'last_name', 'phone_number', 'alternative_phone', 
            'aadhar_number', 'pan_number', 'date_of_birth', 'gender',
            # Business Information
            'business_name', 'business_nature', 'business_registration_number',
            'gst_number', 'business_ownership_type',
            # Address Information
            'address', 'city', 'state', 'pincode', 'landmark',
            # Bank Information
            'bank_name', 'account_number', 'ifsc_code', 'account_holder_name',
        ]
        read_only_fields = ['created_by', 'date_joined']

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
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




class ForgotPasswordSerializer(serializers.Serializer):
    username = serializers.CharField()

class VerifyForgotPasswordOTPSerializer(serializers.Serializer):
    username = serializers.CharField()
    otp = serializers.CharField(max_length=6)

class ResetPasswordSerializer(serializers.Serializer):
    username = serializers.CharField()
    otp = serializers.CharField(max_length=6)
    new_password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    def validate(self, data):
        if data['new_password'] != data['confirm_password']:
            raise serializers.ValidationError("Passwords do not match")
        return data


class StateSerializer(serializers.ModelSerializer):
    class Meta:
        model = State
        fields = ['id', 'name', 'code']

class CitySerializer(serializers.ModelSerializer):
    state_name = serializers.CharField(source='state.name', read_only=True)
    
    class Meta:
        model = City
        fields = ['id', 'name', 'state', 'state_name']