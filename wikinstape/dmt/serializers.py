from rest_framework import serializers
from .models import DMTTransaction, DMTRecipient, DMTServiceCharge
from users.models import User

class DMTRecipientSerializer(serializers.ModelSerializer):
    class Meta:
        model = DMTRecipient
        fields = [
            'id', 'recipient_id', 'name', 'mobile', 'account_number', 
            'ifsc_code', 'bank_name', 'bank_id', 'is_verified', 'is_active',
            'created_at'
        ]
        read_only_fields = ['id', 'recipient_id', 'created_at']

class DMTTransactionSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source='user.username', read_only=True)
    recipient_details = serializers.SerializerMethodField()
    
    class Meta:
        model = DMTTransaction
        fields = [
            'id', 'reference_number', 'eko_transaction_id', 'client_ref_id',
            'customer_mobile', 'customer_name', 'recipient_id', 'recipient_name',
            'recipient_mobile', 'recipient_account', 'recipient_ifsc', 'bank_name',
            'amount', 'service_charge', 'total_amount', 'channel', 'status',
            'eko_status', 'utr_number', 'bank_ref_num', 'response_message',
            'initiated_at', 'processed_at', 'completed_at', 'recipient_details'
        ]
        read_only_fields = [
            'id', 'reference_number', 'eko_transaction_id', 'client_ref_id',
            'status', 'eko_status', 'utr_number', 'bank_ref_num', 'response_message',
            'initiated_at', 'processed_at', 'completed_at'
        ]
    
    def get_recipient_details(self, obj):
        return {
            'name': obj.recipient_name,
            'account_number': obj.recipient_account,
            'ifsc': obj.recipient_ifsc,
            'bank_name': obj.bank_name
        }

class InitiateDMTSerializer(serializers.Serializer):
    customer_mobile = serializers.CharField(max_length=15, required=True)
    recipient_id = serializers.CharField(required=True)
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=1)
    channel = serializers.ChoiceField(choices=[('imps', 'IMPS'), ('neft', 'NEFT')])
    pin = serializers.CharField(max_length=4, required=True)
    latlong = serializers.CharField(required=False, allow_blank=True)
    
    def validate_amount(self, value):
        if value < 1:
            raise serializers.ValidationError("Amount must be at least ₹1")
        if value > 100000: 
            raise serializers.ValidationError("Amount exceeds maximum limit")
        return value
    
    def validate_customer_mobile(self, value):
        if not value.isdigit() or len(value) != 10:
            raise serializers.ValidationError("Invalid mobile number")
        return value

class AddRecipientSerializer(serializers.Serializer):
    customer_mobile = serializers.CharField(max_length=15, required=True)
    name = serializers.CharField(max_length=255, required=True)
    mobile = serializers.CharField(max_length=15, required=True)
    account_number = serializers.CharField(max_length=50, required=True)
    ifsc_code = serializers.CharField(max_length=20, required=True)
    bank_id = serializers.IntegerField(required=True)
    
    def validate_mobile(self, value):
        if not value.isdigit() or len(value) != 10:
            raise serializers.ValidationError("Invalid mobile number")
        return value
    
    def validate_account_number(self, value):
        if not value.isdigit() or len(value) < 9 or len(value) > 18:
            raise serializers.ValidationError("Invalid account number")
        return value
    
    def validate_ifsc_code(self, value):
        if len(value) != 11 or not value[:4].isalpha() or not value[4:].isdigit():
            raise serializers.ValidationError("Invalid IFSC code")
        return value

class VerifyCustomerSerializer(serializers.Serializer):
    customer_mobile = serializers.CharField(max_length=15, required=True)
    otp = serializers.CharField(max_length=6, required=True)

class CalculateChargeSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, required=True)
    
    def validate_amount(self, value):
        if value < 1:
            raise serializers.ValidationError("Amount must be at least ₹1")
        return value