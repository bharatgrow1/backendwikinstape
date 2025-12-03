from rest_framework import serializers

class DMTOnboardSerializer(serializers.Serializer):
    pan_number = serializers.CharField(max_length=10, required=True)
    mobile = serializers.CharField(max_length=15, required=True)
    first_name = serializers.CharField(max_length=100, required=True)
    last_name = serializers.CharField(max_length=100, required=True)
    email = serializers.EmailField(required=True)
    residence_address = serializers.DictField(required=True)
    dob = serializers.CharField(max_length=10, required=True)
    shop_name = serializers.CharField(max_length=255, required=True)


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