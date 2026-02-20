from django.db import models
from django.conf import settings
import uuid


class CreditLinkTransaction(models.Model):

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('failed', 'Failed'),
    ]

    transaction_id = models.CharField(max_length=100, unique=True, blank=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    customer_name = models.CharField(max_length=150)
    customer_mobile = models.CharField(max_length=15)
    customer_pan = models.CharField(max_length=20, blank=True, null=True)
    customer_city = models.CharField(max_length=100, blank=True, null=True)

    commission_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    bank_reference_id = models.CharField(max_length=100, null=True, blank=True)

    redirect_url = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    api_response = models.JSONField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.transaction_id:
            self.transaction_id = f"CL{uuid.uuid4().hex[:12].upper()}"
        super().save(*args, **kwargs)



class Loan(models.Model):

    LOAN_TYPES = (
        ("personal", "Personal"),
        ("gold", "Gold"),
        ("housing", "Housing"),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    loan_type = models.CharField(max_length=20, choices=LOAN_TYPES)

    mobile = models.CharField(max_length=15)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)

    lead_id = models.CharField(max_length=100, unique=True, null=True, blank=True)
    status = models.CharField(max_length=50, default="created")

    commission = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    external_response = models.JSONField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.loan_type} - {self.mobile}"