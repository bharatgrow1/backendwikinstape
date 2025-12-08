from django.db import models
from django.utils import timezone
import uuid
from users.models import User, Wallet

class VendorPayment(models.Model):
    STATUS_CHOICES = (
        ('initiated', 'Initiated'),
        ('processing', 'Processing'),
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('refund_pending', 'Refund Pending'),
        ('refunded', 'Refunded'),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='vendor_payments')
    eko_tid = models.CharField(max_length=50, blank=True, null=True)
    client_ref_id = models.CharField(max_length=50, unique=True, blank=True, null=True)  # ✅ Allow null
    
    recipient_name = models.CharField(max_length=255)
    recipient_account = models.CharField(max_length=50)
    recipient_ifsc = models.CharField(max_length=11)
    
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    processing_fee = models.DecimalField(max_digits=10, decimal_places=2, default=7.00)
    gst = models.DecimalField(max_digits=10, decimal_places=2, default=1.26)
    total_fee = models.DecimalField(max_digits=10, decimal_places=2, default=8.26)
    total_deduction = models.DecimalField(max_digits=12, decimal_places=2)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='initiated')
    status_message = models.TextField(blank=True, null=True)
    transaction_reference = models.CharField(max_length=100, blank=True, null=True)
    
    bank_ref_num = models.CharField(max_length=50, blank=True, null=True)
    utr_number = models.CharField(max_length=50, blank=True, null=True)
    
    payment_date = models.DateTimeField(default=timezone.now)
    timestamp = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    purpose = models.CharField(max_length=255, default="Vendor Payment")
    remarks = models.TextField(blank=True, null=True)
    payment_mode = models.CharField(max_length=10, default='AUTO')
    
    receipt_number = models.CharField(max_length=50, unique=True, blank=True, null=True)
    is_receipt_generated = models.BooleanField(default=False)
    receipt_generated_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['client_ref_id']),
        ]
    
    def __str__(self):
        return f"{self.client_ref_id or 'N/A'} - ₹{self.amount} - {self.status}"
    
    def save(self, *args, **kwargs):
        # ✅ FIXED: Generate client_ref_id if not provided
        if not self.client_ref_id:
            self.client_ref_id = f"VP{int(timezone.now().timestamp())}"
        
        # ✅ FIXED: Calculate total deduction if not provided
        if not self.total_deduction:
            self.total_deduction = self.amount + self.total_fee
        
        # Save first to get ID
        super().save(*args, **kwargs)
        
        # ✅ FIXED: Generate receipt_number AFTER saving (when ID exists)
        if not self.receipt_number:
            self.receipt_number = f"VP{self.id:08d}"
            # Save again with receipt number
            super().save(update_fields=['receipt_number'])
    
    def generate_receipt_data(self):
        """Generate data for receipt PDF"""
        return {
            'receipt_number': self.receipt_number or 'Pending',
            'date': self.payment_date.strftime('%d/%m/%Y %H:%M:%S'),
            'user': {
                'name': self.user.get_full_name() or self.user.username,
                'phone': self.user.phone_number or 'N/A',
                'email': self.user.email or 'N/A'
            },
            'recipient': {
                'name': self.recipient_name,
                'account': self.recipient_account[-4:].rjust(len(self.recipient_account), '*'),
                'ifsc': self.recipient_ifsc,
                'bank_ref': self.bank_ref_num or 'Pending'
            },
            'amount_details': {
                'transfer_amount': float(self.amount),
                'processing_fee': float(self.processing_fee),
                'gst': float(self.gst),
                'total_fee': float(self.total_fee),
                'total_deducted': float(self.total_deduction)
            },
            'transaction': {
                'id': self.client_ref_id,
                'eko_tid': self.eko_tid or 'N/A',
                'status': self.status,
                'mode': self.payment_mode,
                'purpose': self.purpose
            }
        }