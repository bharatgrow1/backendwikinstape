from rest_framework import serializers
from .models import EkoUser, EkoService, EkoTransaction

class EkoUserSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source='user.username', read_only=True)
    
    class Meta:
        model = EkoUser
        fields = ['id', 'user', 'user_username', 'eko_user_code', 'is_verified', 'created_at']

class EkoServiceSerializer(serializers.ModelSerializer):
    service_name = serializers.CharField(source='service_subcategory.name', read_only=True)
    category_name = serializers.CharField(source='service_subcategory.category.name', read_only=True)
    
    class Meta:
        model = EkoService
        fields = ['id', 'service_subcategory', 'service_name', 'category_name', 
                 'eko_service_code', 'eko_service_name', 'is_active']

class EkoTransactionSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source='user.username', read_only=True)
    service_name = serializers.CharField(source='eko_service.service_subcategory.name', read_only=True)
    
    class Meta:
        model = EkoTransaction
        fields = ['id', 'transaction_id', 'user', 'user_username', 'eko_service', 
                 'service_name', 'eko_reference_id', 'client_ref_id', 'amount', 
                 'status', 'response_data', 'created_at', 'updated_at']

# Request Serializers
class EkoOnboardSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()

class BBPSFetchBillSerializer(serializers.Serializer):
    consumer_number = serializers.CharField(max_length=50)
    service_type = serializers.ChoiceField(choices=[
        ('electricity', 'Electricity'),
        ('water', 'Water'), 
        ('gas', 'Gas'),
        ('broadband', 'Broadband')
    ])

class BBPSPayBillSerializer(serializers.Serializer):
    consumer_number = serializers.CharField(max_length=50)
    service_provider = serializers.CharField(max_length=100)
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    bill_number = serializers.CharField(required=False)

class RechargeSerializer(serializers.Serializer):
    mobile_number = serializers.CharField(max_length=10)
    operator_id = serializers.CharField(max_length=20)
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    circle = serializers.CharField(max_length=50, default='DELHI')

class MoneyTransferSerializer(serializers.Serializer):
    account_number = serializers.CharField(max_length=50)
    ifsc_code = serializers.CharField(max_length=11)
    recipient_name = serializers.CharField(max_length=100)
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    payment_mode = serializers.ChoiceField(
        choices=[('imps', 'IMPS'), ('neft', 'NEFT'), ('rtgs', 'RTGS')],
        default='imps'
    )


class ResendOTPSerializer(serializers.Serializer):
    customer_mobile = serializers.CharField(max_length=10, min_length=10)

class CheckStatusSerializer(serializers.Serializer):
    client_ref_id = serializers.CharField(max_length=100)

class RefundSerializer(serializers.Serializer):
    transaction_id = serializers.CharField(max_length=100)
    otp = serializers.CharField(max_length=6, min_length=6)