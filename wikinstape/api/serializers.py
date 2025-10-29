from rest_framework import serializers
from .models import SignUPRequest

class SignUPRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = SignUPRequest
        fields = '__all__'
        read_only_fields = ['id', 'created_at']