from django.db import models
from django.conf import settings


class CMSBiller(models.Model):
    BILLER_TYPE = [
        ("agent", "Agent"),
        ("customer", "Customer"),
    ]

    biller_id = models.CharField(max_length=20, unique=True)
    operator_name = models.CharField(max_length=255)

    company_name = models.CharField(max_length=255)
    biller_type = models.CharField(max_length=20, choices=BILLER_TYPE)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["company_name"]

    def __str__(self):
        return f"{self.company_name} ({self.biller_id})"


class CMSTransaction(models.Model):

    STATUS_CHOICES = [
        ("initiated", "Initiated"),
        ("redirected", "Redirected"),
        ("processing", "Processing"),
        ("success", "Success"),
        ("failed", "Failed"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="cms_transactions"
    )

    client_ref_id = models.CharField(max_length=100, unique=True)
    tid = models.CharField(max_length=50, blank=True, null=True)

    # 🔥 IMPORTANT CHANGE
    biller = models.ForeignKey(
        CMSBiller,
        on_delete=models.PROTECT,
        related_name="transactions"
    )

    amount = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    commission = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="initiated"
    )

    debit_hook_payload = models.JSONField(null=True, blank=True)
    callback_payload = models.JSONField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"CMS {self.client_ref_id} ({self.status})"
