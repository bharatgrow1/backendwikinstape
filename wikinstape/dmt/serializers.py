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