from rest_framework import serializers

class VendorPaymentSerializer(serializers.Serializer):
    recipient_name = serializers.CharField()
    account = serializers.CharField()
    ifsc = serializers.CharField()
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    payment_mode = serializers.IntegerField()
    pin = serializers.CharField(max_length=4, min_length=4, write_only=True, required=True)
    purpose = serializers.CharField(required=False, allow_blank=True, default="Vendor Payment")
    remarks = serializers.CharField(required=False, allow_blank=True, default="")
    
    def validate_pin(self, value):
        if not value.isdigit():
            raise serializers.ValidationError("PIN must contain only digits")
        if len(value) != 4:
            raise serializers.ValidationError("PIN must be exactly 4 digits")
        return value