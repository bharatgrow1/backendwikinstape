from django.db import models
from django.utils import timezone
import uuid

class VendorPayment(models.Model):
    STATUS_CHOICES = (
        ('initiated', 'Initiated'),
        ('processing', 'Processing'),
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('refund_pending', 'Refund Pending'),
        ('refunded', 'Refunded'),
    )

    eko_tid = models.CharField(max_length=50, blank=True, null=True)
    client_ref_id = models.CharField(max_length=50, unique=True)

    recipient_name = models.CharField(max_length=255)
    recipient_account = models.CharField(max_length=50)
    recipient_ifsc = models.CharField(max_length=11)

    amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='initiated')
    status_message = models.TextField(blank=True, null=True)

    bank_ref_num = models.CharField(max_length=50, blank=True, null=True)
    timestamp = models.CharField(max_length=100, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.client_ref_id} - {self.amount} - {self.status}"
