from rest_framework import serializers
from .models import EkoUser, EkoService, EkoTransaction, EkoRecipient

class EkoUserSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source='user.username', read_only=True)
    user_mobile = serializers.CharField(source='user.phone_number', read_only=True)
    
    class Meta:
        model = EkoUser
        fields = ['id', 'user', 'user_username', 'user_mobile', 'eko_user_code', 'is_verified', 'created_at']

class EkoServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = EkoService
        fields = ['id', 'service_code', 'service_name', 'service_type', 'is_active']

class EkoTransactionSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source='user.username', read_only=True)
    
    class Meta:
        model = EkoTransaction
        fields = ['id', 'transaction_id', 'user', 'user_username', 'transaction_type', 
                 'eko_reference_id', 'client_ref_id', 'amount', 'status', 
                 'response_data', 'created_at', 'updated_at']

class EkoRecipientSerializer(serializers.ModelSerializer):
    class Meta:
        model = EkoRecipient
        fields = ['id', 'recipient_id', 'recipient_name', 'account_number', 
                 'ifsc_code', 'recipient_mobile', 'bank_name', 'is_verified', 'created_at']

class EkoOnboardSerializer(serializers.Serializer):
    pan_number = serializers.CharField(max_length=10, required=False)
    business_name = serializers.CharField(max_length=100, required=False)

class DMTValidateAccountSerializer(serializers.Serializer):
    account_number = serializers.CharField(max_length=50)
    ifsc_code = serializers.CharField(max_length=11)

class DMTAddRecipientSerializer(serializers.Serializer):
    account_number = serializers.CharField(max_length=50)
    ifsc_code = serializers.CharField(max_length=11)
    recipient_name = serializers.CharField(max_length=100)
    recipient_mobile = serializers.CharField(max_length=10)
    bank_id = serializers.IntegerField()

class DMTTransferMoneySerializer(serializers.Serializer):
    recipient_id = serializers.CharField(max_length=50)
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    channel = serializers.ChoiceField(choices=[(1, 'NEFT'), (2, 'IMPS')], default=2)

class RechargeSerializer(serializers.Serializer):
    mobile_number = serializers.CharField(max_length=10)
    operator_id = serializers.CharField(max_length=20)
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    circle = serializers.CharField(max_length=50, default='DELHI')

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