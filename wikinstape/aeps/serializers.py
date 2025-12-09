from rest_framework import serializers
from .models import AEPSMerchant

class AEPSMerchantSerializer(serializers.ModelSerializer):
    class Meta:
        model = AEPSMerchant
        fields = '__all__'
        read_only_fields = ['user_code', 'created_at']


class OnboardMerchantSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=100)
    last_name = serializers.CharField(max_length=100, required=False, allow_blank=True)
    middle_name = serializers.CharField(max_length=100, required=False, allow_blank=True)
    mobile = serializers.CharField(max_length=15)
    email = serializers.EmailField()
    pan_number = serializers.CharField(max_length=10)
    shop_name = serializers.CharField(max_length=255)
    dob = serializers.DateField(format='%Y-%m-%d')

    address_line = serializers.CharField()
    city = serializers.CharField(max_length=100)
    state = serializers.CharField(max_length=100)
    pincode = serializers.CharField(max_length=10)
    district = serializers.CharField(max_length=100, required=False, allow_blank=True)
    area = serializers.CharField(max_length=100, required=False, allow_blank=True)
