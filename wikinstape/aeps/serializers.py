# aeps/serializers.py
from rest_framework import serializers
from .models import AEPSMerchant, AEPSTransaction

class AEPSMerchantSerializer(serializers.ModelSerializer):
    class Meta:
        model = AEPSMerchant
        fields = '__all__'
        read_only_fields = ['user_code', 'created_at', 'updated_at']


class OnboardMerchantSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=100)
    last_name = serializers.CharField(max_length=100, required=False, allow_blank=True)
    middle_name = serializers.CharField(max_length=100, required=False, allow_blank=True)
    mobile = serializers.CharField(max_length=15)
    email = serializers.EmailField()
    pan_number = serializers.CharField(max_length=10)
    shop_name = serializers.CharField(max_length=255)
    dob = serializers.DateField(format='%Y-%m-%d')
    
    # Address fields
    address_line = serializers.CharField()
    city = serializers.CharField(max_length=100)
    state = serializers.CharField(max_length=100)
    pincode = serializers.CharField(max_length=10)
    district = serializers.CharField(max_length=100, required=False, allow_blank=True)
    area = serializers.CharField(max_length=100, required=False, allow_blank=True)


class CashWithdrawalSerializer(serializers.Serializer):
    aadhaar_number = serializers.CharField(max_length=12)
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    bank_identifier = serializers.CharField(max_length=50)
    customer_name = serializers.CharField(max_length=255, required=False)
    customer_mobile = serializers.CharField(max_length=15, required=False)
    bank_name = serializers.CharField(max_length=100, required=False)
    latitude = serializers.CharField(max_length=20, required=False)
    longitude = serializers.CharField(max_length=20, required=False)
    device_info = serializers.CharField(required=False)
    location = serializers.CharField(required=False)
    fingerprint_data = serializers.CharField(required=False)
    terminal_id = serializers.CharField(required=False)


class BalanceEnquirySerializer(serializers.Serializer):
    aadhaar_number = serializers.CharField(max_length=12)
    bank_identifier = serializers.CharField(max_length=50)
    customer_name = serializers.CharField(max_length=255, required=False)
    customer_mobile = serializers.CharField(max_length=15, required=False)
    bank_name = serializers.CharField(max_length=100, required=False)
    latitude = serializers.CharField(max_length=20, required=False)
    longitude = serializers.CharField(max_length=20, required=False)
    device_info = serializers.CharField(required=False)
    location = serializers.CharField(required=False)
    fingerprint_data = serializers.CharField(required=False)
    terminal_id = serializers.CharField(required=False)


class TransactionStatusSerializer(serializers.Serializer):
    client_ref_id = serializers.CharField(max_length=50)


class AEPSTransactionSerializer(serializers.ModelSerializer):
    merchant_name = serializers.CharField(source='merchant.merchant_name', read_only=True)
    shop_name = serializers.CharField(source='merchant.shop_name', read_only=True)
    
    class Meta:
        model = AEPSTransaction
        fields = '__all__'