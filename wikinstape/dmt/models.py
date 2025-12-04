from django.db import models
from django.conf import settings
from django.utils import timezone
import uuid
from decimal import Decimal

class DMTTransaction(models.Model):
    STATUS_CHOICES = (
        ('initiated', 'Initiated'),
        ('otp_sent', 'OTP Sent'),
        ('verified', 'OTP Verified'),
        ('processing', 'Processing'),
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    )
    
    TRANSACTION_TYPE_CHOICES = (
        ('imps', 'IMPS'),
        ('neft', 'NEFT'),
        ('rtgs', 'RTGS'),
    )
    
    # Transaction Information
    transaction_id = models.CharField(max_length=100, unique=True, blank=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='dmt_transactions')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    service_charge = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPE_CHOICES, default='imps')
    
    # Sender Information
    sender_mobile = models.CharField(max_length=15)
    sender_name = models.CharField(max_length=255, blank=True, null=True)
    sender_aadhar = models.CharField(max_length=12, blank=True, null=True)
    
    # Recipient Information
    recipient = models.ForeignKey('DMTRecipient', on_delete=models.CASCADE, related_name='transactions')
    recipient_name = models.CharField(max_length=255)
    recipient_mobile = models.CharField(max_length=15, blank=True, null=True)
    recipient_account = models.CharField(max_length=50)
    recipient_ifsc = models.CharField(max_length=11)
    recipient_bank = models.CharField(max_length=255, blank=True, null=True)
    
    # EKO API References
    eko_customer_id = models.CharField(max_length=100, blank=True, null=True)
    eko_recipient_id = models.IntegerField(blank=True, null=True)
    eko_otp_ref_id = models.CharField(max_length=100, blank=True, null=True)
    eko_kyc_request_id = models.CharField(max_length=100, blank=True, null=True)
    eko_transaction_ref = models.CharField(max_length=100, blank=True, null=True)
    
    # Status Tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='initiated')
    status_message = models.TextField(blank=True, null=True)
    
    # Timestamps
    initiated_at = models.DateTimeField(auto_now_add=True)
    otp_sent_at = models.DateTimeField(blank=True, null=True)
    verified_at = models.DateTimeField(blank=True, null=True)
    processed_at = models.DateTimeField(blank=True, null=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    
    # Response Data
    api_response = models.JSONField(blank=True, null=True)
    error_details = models.JSONField(blank=True, null=True)
    
    class Meta:
        ordering = ['-initiated_at']
        indexes = [
            models.Index(fields=['transaction_id']),
            models.Index(fields=['user', 'initiated_at']),
            models.Index(fields=['status', 'initiated_at']),
            models.Index(fields=['sender_mobile']),
        ]
    
    def __str__(self):
        return f"DMT-{self.transaction_id} - {self.user.username} - ₹{self.amount}"
    
    def save(self, *args, **kwargs):
        if not self.transaction_id:
            self.transaction_id = f"DMT{uuid.uuid4().hex[:12].upper()}"
        if not self.total_amount:
            self.total_amount = self.amount + self.service_charge
        super().save(*args, **kwargs)
    
    def mark_otp_sent(self, otp_ref_id):
        self.status = 'otp_sent'
        self.eko_otp_ref_id = otp_ref_id
        self.otp_sent_at = timezone.now()
        self.save()
    
    def mark_verified(self, kyc_request_id=None):
        self.status = 'verified'
        self.eko_kyc_request_id = kyc_request_id
        self.verified_at = timezone.now()
        self.save()
    
    def mark_success(self, transaction_ref):
        self.status = 'success'
        self.eko_transaction_ref = transaction_ref
        self.completed_at = timezone.now()
        self.save()
    
    def mark_failed(self, error_message, error_details=None):
        self.status = 'failed'
        self.status_message = error_message
        self.error_details = error_details or {}
        self.completed_at = timezone.now()
        self.save()

class DMTRecipient(models.Model):
    ACCOUNT_TYPE_CHOICES = (
        (1, 'Savings Account'),
        (2, 'Current Account'),
        (3, 'Salary Account'),
    )
    
    RECIPIENT_TYPE_CHOICES = (
        (1, 'Individual'),
        (2, 'Corporate'),
        (3, 'Other'),
    )
    
    # Basic Information
    recipient_id = models.CharField(max_length=100, unique=True, blank=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='dmt_recipients')
    name = models.CharField(max_length=255)
    mobile = models.CharField(max_length=15, blank=True, null=True)
    
    # Bank Account Details
    account_number = models.CharField(max_length=50)
    confirm_account_number = models.CharField(max_length=50, blank=True, null=True)
    ifsc_code = models.CharField(max_length=11)
    bank_name = models.CharField(max_length=255, blank=True, null=True)
    bank_id = models.IntegerField(blank=True, null=True)
    account_type = models.IntegerField(choices=ACCOUNT_TYPE_CHOICES, default=1)
    recipient_type = models.IntegerField(choices=RECIPIENT_TYPE_CHOICES, default=1)
    
    # EKO API Reference
    eko_recipient_id = models.IntegerField(blank=True, null=True)
    eko_verification_status = models.CharField(max_length=20, default='pending', choices=(
        ('pending', 'Pending'),
        ('verified', 'Verified'),
        ('failed', 'Failed'),
    ))
    
    # Status
    is_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    verified_at = models.DateTimeField(blank=True, null=True)
    
    # Additional Info
    verification_response = models.JSONField(blank=True, null=True)
    
    class Meta:
        ordering = ['-created_at']
        unique_together = ['user', 'account_number', 'ifsc_code']
        indexes = [
            models.Index(fields=['recipient_id']),
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['eko_recipient_id']),
        ]
    
    def __str__(self):
        return f"{self.name} - {self.account_number} - {self.user.username}"
    
    def save(self, *args, **kwargs):
        if not self.recipient_id:
            self.recipient_id = f"REC{uuid.uuid4().hex[:10].upper()}"
        super().save(*args, **kwargs)
    
    def mark_verified(self, eko_recipient_id, response_data=None):
        self.eko_recipient_id = eko_recipient_id
        self.is_verified = True
        self.eko_verification_status = 'verified'
        self.verified_at = timezone.now()
        self.verification_response = response_data or {}
        self.save()
    
    def mark_verification_failed(self, response_data=None):
        self.is_verified = False
        self.eko_verification_status = 'failed'
        self.verification_response = response_data or {}
        self.save()

class DMTSenderProfile(models.Model):
    KYC_STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('verified', 'Verified'),
        ('rejected', 'Rejected'),
        ('expired', 'Expired'),
    )
    
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='dmt_sender_profile')
    mobile = models.CharField(max_length=15, unique=True)
    aadhar_number = models.CharField(max_length=12, blank=True, null=True)
    
    # KYC Information
    kyc_status = models.CharField(max_length=20, choices=KYC_STATUS_CHOICES, default='pending')
    kyc_verified_at = models.DateTimeField(blank=True, null=True)
    kyc_method = models.CharField(max_length=20, blank=True, null=True, choices=(
        ('biometric', 'Biometric'),
        ('otp', 'OTP'),
        ('manual', 'Manual'),
    ))
    
    # EKO API Data
    eko_customer_id = models.CharField(max_length=100, blank=True, null=True)
    eko_profile_data = models.JSONField(blank=True, null=True)
    
    # Limits
    daily_limit = models.DecimalField(max_digits=10, decimal_places=2, default=50000.00)
    monthly_limit = models.DecimalField(max_digits=10, decimal_places=2, default=200000.00)
    per_transaction_limit = models.DecimalField(max_digits=10, decimal_places=2, default=25000.00)
    
    # Usage Tracking
    daily_usage = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    monthly_usage = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_transaction_at = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['mobile']),
            models.Index(fields=['kyc_status']),
            models.Index(fields=['eko_customer_id']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.mobile} - {self.kyc_status}"
    
    def reset_limits(self):
        """Reset daily usage (to be called via cron job)"""
        self.daily_usage = Decimal('0.00')
        self.save()
    
    def reset_monthly_usage(self):
        """Reset monthly usage (to be called via cron job)"""
        self.monthly_usage = Decimal('0.00')
        self.save()
    
    def can_transact(self, amount):
        """Check if sender can perform transaction with given amount"""
        if self.kyc_status != 'verified':
            return False, "KYC not verified"
        
        if amount > self.per_transaction_limit:
            return False, f"Amount exceeds per transaction limit of ₹{self.per_transaction_limit}"
        
        if (self.daily_usage + amount) > self.daily_limit:
            return False, f"Amount exceeds daily limit of ₹{self.daily_limit}"
        
        if (self.monthly_usage + amount) > self.monthly_limit:
            return False, f"Amount exceeds monthly limit of ₹{self.monthly_limit}"
        
        return True, "OK"
    
    def update_usage(self, amount):
        """Update usage after successful transaction"""
        self.daily_usage += amount
        self.monthly_usage += amount
        self.last_transaction_at = timezone.now()
        self.save()

class DMTServiceCharge(models.Model):
    AMOUNT_RANGE_CHOICES = (
        ('0-1000', '₹0 - ₹1,000'),
        ('1001-10000', '₹1,001 - ₹10,000'),
        ('10001-25000', '₹10,001 - ₹25,000'),
        ('25001-50000', '₹25,001 - ₹50,000'),
        ('50001-100000', '₹50,001 - ₹1,00,000'),
    )
    
    amount_range = models.CharField(max_length=20, choices=AMOUNT_RANGE_CHOICES, unique=True)
    min_amount = models.DecimalField(max_digits=10, decimal_places=2)
    max_amount = models.DecimalField(max_digits=10, decimal_places=2)
    service_charge = models.DecimalField(max_digits=10, decimal_places=2)
    charge_type = models.CharField(max_length=10, choices=(
        ('fixed', 'Fixed'),
        ('percentage', 'Percentage'),
    ), default='fixed')
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['min_amount']
    
    def __str__(self):
        return f"{self.amount_range} - ₹{self.service_charge}"
    
    @classmethod
    def calculate_charge(cls, amount):
        """Calculate service charge for given amount"""
        try:
            charge_config = cls.objects.filter(
                min_amount__lte=amount,
                max_amount__gte=amount,
                is_active=True
            ).first()
            
            if charge_config:
                if charge_config.charge_type == 'percentage':
                    return (amount * charge_config.service_charge) / 100
                return charge_config.service_charge
            return Decimal('0.00')
        except cls.DoesNotExist:
            return Decimal('0.00')

class DMTBank(models.Model):
    bank_id = models.IntegerField(unique=True)
    bank_name = models.CharField(max_length=255)
    bank_code = models.CharField(max_length=50, blank=True, null=True)
    ifsc_prefix = models.CharField(max_length=10, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['bank_name']
        indexes = [
            models.Index(fields=['bank_name']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return f"{self.bank_name} ({self.bank_id})"
    


class EkoBank(models.Model):
    bank_id = models.IntegerField(primary_key=True)
    bank_name = models.CharField(max_length=255)
    bank_code = models.CharField(max_length=50)
    imps_status = models.CharField(max_length=50)
    neft_status = models.CharField(max_length=50)
    verification_status = models.CharField(max_length=50)
    ifsc_status = models.CharField(max_length=255)
    static_ifsc = models.CharField(max_length=50, null=True, blank=True)

    def __str__(self):
        return self.bank_name