from rest_framework import serializers

class VendorPaymentSerializer(serializers.Serializer):
    recipient_name = serializers.CharField()
    account = serializers.CharField()
    ifsc = serializers.CharField()
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    payment_mode = serializers.IntegerField()
