from rest_framework import serializers
from .models import PersonalLoan


class PersonalLoanSerializer(serializers.ModelSerializer):
    class Meta:
        model = PersonalLoan
        fields = "__all__"
