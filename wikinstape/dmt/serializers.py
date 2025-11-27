from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import (DMTTransaction, DMTRecipient, DMTSenderProfile, 
                    DMTServiceCharge, DMTBank)

User = get_user_model()

class DMTBankSerializer(serializers.ModelSerializer):
    class Meta:
        model = DMTBank
        fields = ['bank_id', 'bank_name', 'bank_code', 'ifsc_prefix', 'is_active']

class DMTServiceChargeSerializer(serializers.ModelSerializer):
    class Meta:
        model = DMTServiceCharge
        fields = ['id', 'amount_range', 'min_amount', 'max_amount', 
                 'service_charge', 'charge_type', 'is_active']

class DMTRecipientSerializer(serializers.ModelSerializer):
    bank_name_display = serializers.CharField(source='bank_name', read_only=True)
    account_type_display = serializers.CharField(source='get_account_type_display', read_only=True)
    verification_status_display = serializers.CharField(source='eko_verification_status', read_only=True)
    
    class Meta:
        model = DMTRecipient
        fields = [
            'recipient_id', 'name', 'mobile', 'account_number', 
            'confirm_account_number', 'ifsc_code', 'bank_name', 'bank_name_display',
            'bank_id', 'account_type', 'account_type_display', 'recipient_type',
            'eko_recipient_id', 'eko_verification_status', 'verification_status_display',
            'is_verified', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['recipient_id', 'eko_recipient_id', 'eko_verification_status', 
                          'is_verified', 'created_at', 'updated_at']

class DMTRecipientCreateSerializer(serializers.ModelSerializer):
    confirm_account_number = serializers.CharField(write_only=True, required=True)
    
    class Meta:
        model = DMTRecipient
        fields = [
            'name', 'mobile', 'account_number', 'confirm_account_number',
            'ifsc_code', 'bank_name', 'bank_id', 'account_type', 'recipient_type'
        ]
    
    def validate(self, data):
        if data['account_number'] != data['confirm_account_number']:
            raise serializers.ValidationError({
                'confirm_account_number': 'Account numbers do not match'
            })
        
        # Check if recipient already exists for this user
        user = self.context['request'].user
        if DMTRecipient.objects.filter(
            user=user, 
            account_number=data['account_number'],
            ifsc_code=data['ifsc_code']
        ).exists():
            raise serializers.ValidationError('Recipient with this account already exists')
        
        return data
    
    def create(self, validated_data):
        validated_data.pop('confirm_account_number', None)
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)

class DMTSenderProfileSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source='user.username', read_only=True)
    kyc_status_display = serializers.CharField(source='get_kyc_status_display', read_only=True)
    
    class Meta:
        model = DMTSenderProfile
        fields = [
            'id', 'user', 'user_username', 'mobile', 'aadhar_number',
            'kyc_status', 'kyc_status_display', 'kyc_verified_at', 'kyc_method',
            'eko_customer_id', 'daily_limit', 'monthly_limit', 'per_transaction_limit',
            'daily_usage', 'monthly_usage', 'last_transaction_at',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['user', 'eko_customer_id', 'daily_usage', 'monthly_usage',
                          'last_transaction_at', 'created_at', 'updated_at']

class DMTTransactionSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source='user.username', read_only=True)
    recipient_name = serializers.CharField(source='recipient.name', read_only=True)
    recipient_account = serializers.CharField(source='recipient.account_number', read_only=True)
    recipient_ifsc = serializers.CharField(source='recipient.ifsc_code', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    transaction_type_display = serializers.CharField(source='get_transaction_type_display', read_only=True)
    
    class Meta:
        model = DMTTransaction
        fields = [
            'transaction_id', 'user', 'user_username', 'amount', 'service_charge',
            'total_amount', 'transaction_type', 'transaction_type_display',
            'sender_mobile', 'sender_name', 'sender_aadhar',
            'recipient', 'recipient_name', 'recipient_account', 'recipient_ifsc',
            'recipient_name', 'recipient_mobile', 'recipient_account', 'recipient_ifsc',
            'eko_customer_id', 'eko_recipient_id', 'eko_otp_ref_id', 
            'eko_kyc_request_id', 'eko_transaction_ref',
            'status', 'status_display', 'status_message',
            'initiated_at', 'otp_sent_at', 'verified_at', 'processed_at', 'completed_at',
            'api_response', 'error_details'
        ]
        read_only_fields = ['transaction_id', 'user', 'total_amount', 'status',
                          'initiated_at', 'otp_sent_at', 'verified_at', 'processed_at',
                          'completed_at', 'api_response', 'error_details']

class DMTTransactionCreateSerializer(serializers.Serializer):
    recipient_id = serializers.CharField(required=True)
    amount = serializers.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        min_value=1.00,
        max_value=50000.00
    )
    transaction_type = serializers.ChoiceField(
        choices=DMTTransaction.TRANSACTION_TYPE_CHOICES,
        default='imps'
    )
    pin = serializers.CharField(max_length=4, min_length=4, write_only=True, required=True)
    
    def validate(self, data):
        user = self.context['request'].user
        amount = data['amount']
        
        # Check sender profile and limits
        try:
            sender_profile = DMTSenderProfile.objects.get(user=user)
            can_transact, message = sender_profile.can_transact(amount)
            if not can_transact:
                raise serializers.ValidationError({'amount': message})
        except DMTSenderProfile.DoesNotExist:
            raise serializers.ValidationError({'non_field_errors': 'Sender profile not found. Please complete KYC first.'})
        
        # Check recipient
        try:
            recipient = DMTRecipient.objects.get(
                recipient_id=data['recipient_id'],
                user=user,
                is_active=True,
                is_verified=True
            )
            data['recipient'] = recipient
        except DMTRecipient.DoesNotExist:
            raise serializers.ValidationError({'recipient_id': 'Recipient not found or not verified'})
        
        # Verify wallet PIN
        wallet = user.wallet
        service_charge = DMTServiceCharge.calculate_charge(amount)
        total_amount = amount + service_charge
        
        if not wallet.verify_pin(data['pin']):
            raise serializers.ValidationError({'pin': 'Invalid wallet PIN'})
        
        if not wallet.has_sufficient_balance(amount, service_charge):
            raise serializers.ValidationError({
                'amount': 'Insufficient balance including service charges'
            })
        
        data['service_charge'] = service_charge
        data['total_amount'] = total_amount
        data['sender_profile'] = sender_profile
        
        return data

class DMTOTPVerifySerializer(serializers.Serializer):
    transaction_id = serializers.CharField(required=True)
    otp = serializers.CharField(max_length=6, min_length=6, required=True)
    pin = serializers.CharField(max_length=4, min_length=4, write_only=True, required=True)
    
    def validate(self, data):
        user = self.context['request'].user
        
        try:
            transaction = DMTTransaction.objects.get(
                transaction_id=data['transaction_id'],
                user=user,
                status='otp_sent'
            )
            data['transaction'] = transaction
        except DMTTransaction.DoesNotExist:
            raise serializers.ValidationError({
                'transaction_id': 'Transaction not found or invalid status'
            })
        
        # Verify wallet PIN again for security
        wallet = user.wallet
        if not wallet.verify_pin(data['pin']):
            raise serializers.ValidationError({'pin': 'Invalid wallet PIN'})
        
        return data

class DMTBiometricKycSerializer(serializers.Serializer):
    aadhar_number = serializers.CharField(max_length=12, min_length=12, required=True)
    piddata = serializers.CharField(required=True)
    
    def validate_aadhar_number(self, value):
        if not value.isdigit():
            raise serializers.ValidationError("Aadhar number must contain only digits")
        if len(value) != 12:
            raise serializers.ValidationError("Aadhar number must be 12 digits")
        return value

class DMTKycOTPVerifySerializer(serializers.Serializer):
    otp = serializers.CharField(max_length=6, min_length=6, required=True)
    otp_ref_id = serializers.CharField(required=True)
    kyc_request_id = serializers.CharField(required=True)

class DMTLimitSerializer(serializers.Serializer):
    daily_limit = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    monthly_limit = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    per_transaction_limit = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    daily_usage = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    monthly_usage = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    available_daily = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    available_monthly = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)