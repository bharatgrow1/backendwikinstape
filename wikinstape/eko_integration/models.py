from django.db import models
from users.models import User
from services.models import ServiceSubCategory
import uuid
from django.utils import timezone

class EkoUser(models.Model):
    """Store Eko user mapping"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='eko_user')
    eko_user_code = models.CharField(max_length=50, unique=True)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.eko_user_code}"

class EkoService(models.Model):
    """Map our services to Eko services"""
    service_subcategory = models.OneToOneField(ServiceSubCategory, on_delete=models.CASCADE)
    eko_service_code = models.CharField(max_length=20)
    eko_service_name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.service_subcategory.name} - {self.eko_service_name}"

class EkoTransaction(models.Model):
    """Track Eko transactions"""
    STATUS_CHOICES = (
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('pending', 'Pending'),
        ('processing', 'Processing'),
    )
    
    transaction_id = models.UUIDField(default=uuid.uuid4, unique=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    eko_service = models.ForeignKey(EkoService, on_delete=models.CASCADE)
    eko_reference_id = models.CharField(max_length=100, blank=True, null=True)
    client_ref_id = models.CharField(max_length=100)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    response_data = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.client_ref_id} - {self.amount}"