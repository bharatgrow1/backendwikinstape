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
    bank_reference_id = models.CharField(max_length=100,null=True,blank=True)
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



class PersonalLoan(models.Model):
    EMPLOYMENT_CHOICES = (
        ("salaried", "Salaried"),
        ("self-employed", "Self Employed"),
    )

    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    mobile = models.CharField(max_length=10)
    email = models.EmailField()
    pan_number = models.CharField(max_length=10)
    dob = models.DateField()
    credit_score = models.IntegerField(null=True, blank=True)
    pincode = models.CharField(max_length=6)

    employment_status = models.CharField(max_length=20, choices=EMPLOYMENT_CHOICES)
    employer_name = models.CharField(max_length=255)
    office_pin_code = models.CharField(max_length=6)
    monthly_income = models.IntegerField()

    external_lead_id = models.CharField(max_length=100, null=True, blank=True)
    external_response = models.JSONField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.first_name} - {self.mobile}"
