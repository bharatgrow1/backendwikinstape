# aeps/models.py
from django.db import models
from django.utils import timezone

class AEPSMerchant(models.Model):
    STATUS_CHOICES = (
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('suspended', 'Suspended'),
    )
    
    user_code = models.CharField(max_length=20, unique=True)
    merchant_name = models.CharField(max_length=255)
    shop_name = models.CharField(max_length=255)
    mobile = models.CharField(max_length=15)
    email = models.EmailField()
    pan_number = models.CharField(max_length=10)
    
    # Address fields
    address_line = models.TextField()
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    pincode = models.CharField(max_length=10)
    district = models.CharField(max_length=100, blank=True, null=True)
    area = models.CharField(max_length=100, blank=True, null=True)
    
    # Bank details (for commission settlement)
    bank_account = models.CharField(max_length=50, blank=True, null=True)
    bank_ifsc = models.CharField(max_length=11, blank=True, null=True)
    bank_name = models.CharField(max_length=100, blank=True, null=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.merchant_name} ({self.user_code})"


class AEPSTransaction(models.Model):
    TRANSACTION_TYPES = (
        ('cash_withdrawal', 'Cash Withdrawal'),
        ('balance_enquiry', 'Balance Enquiry'),
        ('mini_statement', 'Mini Statement'),
        ('cash_deposit', 'Cash Deposit'),
        ('aadhaar_pay', 'Aadhaar Pay'),
        ('imps', 'IMPS'),
    )
    
    STATUS_CHOICES = (
        ('initiated', 'Initiated'),
        ('processing', 'Processing'),
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('reversed', 'Reversed'),
    )
    
    # Transaction identifiers
    eko_tid = models.CharField(max_length=50, unique=True)
    client_ref_id = models.CharField(max_length=50, unique=True)
    bank_rrn = models.CharField(max_length=50, blank=True, null=True)
    bank_ref_num = models.CharField(max_length=50, blank=True, null=True)
    
    # Merchant details
    merchant = models.ForeignKey(AEPSMerchant, on_delete=models.CASCADE, related_name='transactions')
    initiator_id = models.CharField(max_length=15)
    
    # Customer details
    customer_aadhaar = models.CharField(max_length=12)
    customer_name = models.CharField(max_length=255, blank=True, null=True)
    customer_mobile = models.CharField(max_length=15, blank=True, null=True)
    
    # Transaction details
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    service_charge = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    commission = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Bank details
    bank_identifier = models.CharField(max_length=50)  # Bank IIN or code
    bank_name = models.CharField(max_length=100, blank=True, null=True)
    
    # Status and response
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='initiated')
    status_code = models.CharField(max_length=10, blank=True, null=True)
    status_message = models.TextField(blank=True, null=True)
    response_data = models.JSONField(default=dict, blank=True)
    
    # Timestamps
    initiated_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.client_ref_id} - {self.transaction_type} - {self.amount}"