from django.db import models
from django.conf import settings
import uuid
from django.utils import timezone
from decimal import Decimal

class DMTTransaction(models.Model):
    STATUS_CHOICES = (
        ('initiated', 'Initiated'),
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('pending', 'Pending'),
        ('refund_pending', 'Refund Pending'),
        ('refunded', 'Refunded'),
        ('hold', 'Hold'),
    )
    
    CHANNEL_CHOICES = (
        ('imps', 'IMPS'),
        ('neft', 'NEFT'),
    )
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='dmt_transactions')
    reference_number = models.CharField(max_length=100, unique=True)
    eko_transaction_id = models.CharField(max_length=100, blank=True, null=True)
    client_ref_id = models.CharField(max_length=100, unique=True)
    
    customer_mobile = models.CharField(max_length=15)
    customer_id = models.CharField(max_length=100, blank=True, null=True)
    
    recipient_id = models.CharField(max_length=100)
    recipient_name = models.CharField(max_length=255)
    recipient_mobile = models.CharField(max_length=15)
    recipient_account = models.CharField(max_length=50)
    recipient_ifsc = models.CharField(max_length=20)
    bank_name = models.CharField(max_length=255)
    bank_id = models.IntegerField()
    
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    service_charge = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    
    channel = models.CharField(max_length=10, choices=CHANNEL_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='initiated')
    eko_status = models.IntegerField(null=True, blank=True)
    
    utr_number = models.CharField(max_length=100, blank=True, null=True)
    bank_ref_num = models.CharField(max_length=100, blank=True, null=True)
    response_message = models.TextField(blank=True, null=True)
    
    initiated_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField(blank=True, null=True)
    latlong = models.CharField(max_length=100, blank=True, null=True)
    
    class Meta:
        ordering = ['-initiated_at']
        indexes = [
            models.Index(fields=['reference_number']),
            models.Index(fields=['customer_mobile']),
            models.Index(fields=['status', 'initiated_at']),
            models.Index(fields=['eko_transaction_id']),
        ]
    
    def __str__(self):
        return f"DMT-{self.reference_number} - ₹{self.amount}"
    
    def save(self, *args, **kwargs):
        if not self.reference_number:
            self.reference_number = self.generate_reference_number()
        if not self.client_ref_id:
            self.client_ref_id = self.generate_client_ref_id()
        if not self.total_amount:
            self.total_amount = self.amount + self.service_charge
        super().save(*args, **kwargs)
    
    def generate_reference_number(self):
        return f"DMT{timezone.now().strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:6].upper()}"
    
    def generate_client_ref_id(self):
        return f"CL{timezone.now().strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:8].upper()}"

class DMTRecipient(models.Model):
    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='dmt_recipients')
    recipient_id = models.CharField(max_length=100)
    name = models.CharField(max_length=255)
    mobile = models.CharField(max_length=15)
    account_number = models.CharField(max_length=50)
    ifsc_code = models.CharField(max_length=20)
    bank_name = models.CharField(max_length=255)
    bank_id = models.IntegerField()
    is_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['customer', 'account_number', 'ifsc_code']
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} - {self.account_number}"

class DMTServiceCharge(models.Model):
    amount_from = models.DecimalField(max_digits=10, decimal_places=2)
    amount_to = models.DecimalField(max_digits=10, decimal_places=2)
    charge_type = models.CharField(max_length=10, choices=[('fixed', 'Fixed'), ('percentage', 'Percentage')])
    charge_value = models.DecimalField(max_digits=10, decimal_places=2)
    min_charge = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    max_charge = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['amount_from']
    
    def calculate_charge(self, amount):
        if self.charge_type == 'fixed':
            charge = self.charge_value
        else:
            charge = (amount * self.charge_value) / 100
        
        if self.min_charge and charge < self.min_charge:
            charge = self.min_charge
        if self.max_charge and charge > self.max_charge:
            charge = self.max_charge
        
        return charge