from django.db import models
from users.models import User
import uuid
from django.utils import timezone

class EkoUser(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='eko_user')
    eko_user_code = models.CharField(max_length=50, unique=True)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.eko_user_code}"

class EkoService(models.Model):
    SERVICE_CHOICES = (
        ('dmt', 'Money Transfer'),
        ('recharge', 'Mobile Recharge'),
        ('bbps', 'BBPS Bill Payment'),
    )
    
    service_code = models.CharField(max_length=20, unique=True)
    service_name = models.CharField(max_length=100)
    service_type = models.CharField(max_length=20, choices=SERVICE_CHOICES)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.service_name} - {self.service_code}"

class EkoTransaction(models.Model):
    TRANSACTION_STATUS = (
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('pending', 'Pending'),
        ('processing', 'Processing'),
    )
    
    TRANSACTION_TYPES = (
        ('onboard', 'User Onboarding'),
        ('dmt', 'Money Transfer'),
        ('recharge', 'Mobile Recharge'),
        ('bbps', 'BBPS Payment'),
        ('balance_check', 'Balance Check'),
    )
    
    transaction_id = models.UUIDField(default=uuid.uuid4, unique=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    eko_reference_id = models.CharField(max_length=100, blank=True, null=True)
    client_ref_id = models.CharField(max_length=100)
    amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    status = models.CharField(max_length=20, choices=TRANSACTION_STATUS, default='pending')
    response_data = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.client_ref_id} - {self.amount}"

class EkoRecipient(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='eko_recipients')
    recipient_id = models.CharField(max_length=50)
    recipient_name = models.CharField(max_length=100)
    account_number = models.CharField(max_length=50)
    ifsc_code = models.CharField(max_length=11)
    recipient_mobile = models.CharField(max_length=10)
    bank_name = models.CharField(max_length=100)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['user', 'account_number', 'ifsc_code']
    
    def __str__(self):
        return f"{self.recipient_name} - {self.account_number}"