from rest_framework import serializers
from .models import CMSTransaction, CMSBiller


class GenerateCMSUrlSerializer(serializers.Serializer):
    biller_id = serializers.CharField()
    latlong = serializers.CharField()

    def validate_biller_id(self, value):
        if not CMSBiller.objects.filter(biller_id=value, is_active=True).exists():
            raise serializers.ValidationError("Invalid or inactive CMS biller")
        return value


class CMSTransactionSerializer(serializers.ModelSerializer):
    biller_name = serializers.CharField(source="biller.company_name", read_only=True)
    biller_type = serializers.CharField(source="biller.biller_type", read_only=True)

    class Meta:
        model = CMSTransaction
        fields = "__all__"
        read_only_fields = [
            "client_ref_id", "tid", "status",
            "commission", "created_at"
        ]
