from rest_framework import serializers
from .models import EkoBank, DMTTransaction

class DMTOnboardSerializer(serializers.Serializer):
    pan_number = serializers.CharField(max_length=10, required=True)
    mobile = serializers.CharField(max_length=15, required=True)
    first_name = serializers.CharField(max_length=100, required=True)
    last_name = serializers.CharField(max_length=100, required=True)
    email = serializers.EmailField(required=True)
    residence_address = serializers.DictField(required=True)
    dob = serializers.CharField(max_length=10, required=True)
    shop_name = serializers.CharField(max_length=255, required=True)


class DMTVerifyCustomerSerializer(serializers.Serializer):
    customer_mobile = serializers.CharField(max_length=10, required=True)
    otp = serializers.CharField(max_length=6, required=True)
    otp_ref_id = serializers.CharField(required=True)

class DMTResendOTPSerializer(serializers.Serializer):
    customer_mobile = serializers.CharField(max_length=10, required=True)


class DMTCreateCustomerSerializer(serializers.Serializer):
    mobile = serializers.CharField(max_length=10, required=True)
    name = serializers.CharField(max_length=200, required=True)
    dob = serializers.CharField(max_length=10, required=True)
    address_line = serializers.CharField(max_length=255, required=False, allow_blank=True)
    city = serializers.CharField(max_length=100, required=True)
    state = serializers.CharField(max_length=100, required=True)
    pincode = serializers.CharField(max_length=6, required=True)
    district = serializers.CharField(max_length=100, required=False, allow_blank=True)
    area = serializers.CharField(max_length=100, required=False, allow_blank=True)
    skip_verification = serializers.BooleanField(default=False, required=False)
    
    def validate_mobile(self, value):
        if len(value) != 10:
            raise serializers.ValidationError("Mobile number must be 10 digits")
        if not value.isdigit():
            raise serializers.ValidationError("Mobile number must contain only digits")
        return value
    
    def validate_dob(self, value):
        try:
            from datetime import datetime
            datetime.strptime(value, '%Y-%m-%d')
        except ValueError:
            raise serializers.ValidationError("DOB must be in YYYY-MM-DD format")
        return value
    
    def validate_pincode(self, value):
        if len(value) != 6:
            raise serializers.ValidationError("Pincode must be 6 digits")
        if not value.isdigit():
            raise serializers.ValidationError("Pincode must contain only digits")
        return value
    

class DMTGetProfileSerializer(serializers.Serializer):
    customer_mobile = serializers.CharField(max_length=15, required=True)

class DMTBiometricKycSerializer(serializers.Serializer):
    customer_id = serializers.CharField(max_length=15, required=True)
    aadhar = serializers.CharField(max_length=12, required=True)
    piddata = serializers.CharField(required=True)

class DMTKycOTPVerifySerializer(serializers.Serializer):
    customer_id = serializers.CharField(max_length=15, required=True)
    otp = serializers.CharField(max_length=6, required=True)
    otp_ref_id = serializers.CharField(required=True)
    kyc_request_id = serializers.CharField(required=True)

class DMTAddRecipientSerializer(serializers.Serializer):
    customer_id = serializers.CharField(max_length=15, required=True)
    recipient_name = serializers.CharField(max_length=255, required=True)
    recipient_mobile = serializers.CharField(max_length=15, required=False, allow_blank=True)
    account = serializers.CharField(max_length=50, required=True)
    ifsc = serializers.CharField(max_length=11, required=True)
    bank_id = serializers.IntegerField(required=True)
    account_type = serializers.IntegerField(default=1)
    recipient_type = serializers.IntegerField(default=3)

class DMTGetRecipientsSerializer(serializers.Serializer):
    customer_id = serializers.CharField(max_length=15, required=True)

class DMTSendTxnOTPSerializer(serializers.Serializer):
    customer_id = serializers.CharField(max_length=15, required=True)
    recipient_id = serializers.IntegerField(required=True)
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, required=True)

class DMTInitiateTransactionSerializer(serializers.Serializer):
    customer_id = serializers.CharField(max_length=15, required=True)
    recipient_id = serializers.IntegerField(required=True)
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, required=True)
    otp = serializers.CharField(max_length=6, required=True)
    otp_ref_id = serializers.CharField(required=True)
    pin = serializers.CharField(max_length=4, min_length=4, write_only=True, required=True)
    
    def validate_pin(self, value):
        if not value.isdigit():
            raise serializers.ValidationError("PIN must contain only digits")
        if len(value) != 4:
            raise serializers.ValidationError("PIN must be exactly 4 digits")
        return value
    

class DMTTransactionSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source='user.username', read_only=True)
    recipient_name = serializers.CharField(source='recipient.name', read_only=True)
    recipient_account = serializers.CharField(source='recipient.account_number', read_only=True)
    recipient_ifsc = serializers.CharField(source='recipient.ifsc_code', read_only=True)
    wallet_transaction_ref = serializers.CharField(source='wallet_transaction.reference_number', read_only=True)
    
    class Meta:
        model = DMTTransaction
        fields = [
            'id',
            'transaction_id',
            'user',
            'user_username',
            'amount',
            'service_charge',
            'total_amount',
            'sender_mobile',
            'recipient',
            'recipient_name',
            'recipient_account',
            'recipient_ifsc',
            'eko_tid',
            'client_ref_id',
            'eko_bank_ref_num',
            'status',
            'status_message',
            'eko_txstatus_desc',
            'wallet_transaction',
            'wallet_transaction_ref',
            'initiated_at',
            'completed_at',
        ]
        read_only_fields = fields


class EkoBankSerializer(serializers.ModelSerializer):
    class Meta:
        model = EkoBank
        fields = ["bank_id", "bank_name", "bank_code", "static_ifsc"]


class DMTTransactionInquirySerializer(serializers.Serializer):
    inquiry_id = serializers.CharField(required=True)
    is_client_ref_id = serializers.BooleanField(default=False, required=False)
    
    def validate_inquiry_id(self, value):
        if not value:
            raise serializers.ValidationError("Inquiry ID cannot be empty")
        return value
    

class DMTRefundSerializer(serializers.Serializer):
    tid = serializers.CharField(required=True)
    otp = serializers.CharField(required=True)


class DMTRefundOTPResendSerializer(serializers.Serializer):
    tid = serializers.CharField(required=True)
