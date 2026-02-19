from rest_framework import serializers
from .models import PersonalLoan
from .models import CreditLinkTransaction


class CreditApplySerializer(serializers.Serializer):
    name = serializers.CharField()
    mobile = serializers.CharField()
    pan = serializers.CharField(required=False, allow_blank=True)
    city = serializers.CharField(required=False, allow_blank=True)


class CreditLinkResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = CreditLinkTransaction
        fields = "__all__"



class PersonalLoanSerializer(serializers.ModelSerializer):
    class Meta:
        model = PersonalLoan
        fields = "__all__"
