from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from decimal import Decimal
from users.models import User
import random
from django.core.exceptions import ValidationError


class CommissionPlan(models.Model):
    PLAN_TYPES = (
        ('platinum', 'Platinum'),
        ('gold', 'Gold'),
        ('silver', 'Silver'),
    )
    
    name = models.CharField(max_length=100)
    plan_type = models.CharField(max_length=20, choices=PLAN_TYPES, unique=True)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.name} ({self.plan_type})"

class ServiceCommission(models.Model):
    COMMISSION_TYPES = (
        ('percentage', 'Percentage'),
        ('fixed', 'Fixed Amount'),
    )
    
    service_category = models.ForeignKey('services.ServiceCategory', on_delete=models.CASCADE, null=True, blank=True)
    service_subcategory = models.ForeignKey('services.ServiceSubCategory', on_delete=models.CASCADE, null=True, blank=True)
    
    commission_plan = models.ForeignKey(CommissionPlan, on_delete=models.CASCADE)
    
    commission_type = models.CharField(max_length=20, choices=COMMISSION_TYPES, default='percentage')
    commission_value = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    
    admin_commission = models.DecimalField(
        max_digits=5, decimal_places=2, 
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        default=0
    )
    master_commission = models.DecimalField(
        max_digits=5, decimal_places=2, 
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        default=0
    )
    dealer_commission = models.DecimalField(
        max_digits=5, decimal_places=2, 
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        default=0
    )
    retailer_commission = models.DecimalField(
        max_digits=5, decimal_places=2, 
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        default=0
    )
    
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['service_subcategory', 'commission_plan']
        verbose_name = "Service Commission"
        verbose_name_plural = "Service Commissions"
    
    def __str__(self):
        service_name = self.service_subcategory.name if self.service_subcategory else self.service_category.name
        return f"{service_name} - {self.commission_plan.name} - {self.commission_value}{'%' if self.commission_type == 'percentage' else '₹'}"
    
    def clean(self):
        """Validate commission distribution totals 100%"""
        if self.commission_type == 'percentage':
            total = (
                self.admin_commission + 
                self.master_commission + 
                self.dealer_commission + 
                self.retailer_commission
            )
            if total != 100:
                raise ValidationError("Total commission distribution must equal 100%")
    
    def calculate_commission(self, transaction_amount):
        """Calculate commission based on transaction amount"""
        if self.commission_type == 'percentage':
            commission = (transaction_amount * self.commission_value) / 100
        else:
            commission = self.commission_value
            
        return commission
    
    def distribute_commission(self, transaction_amount, retailer_user):
        """Distribute commission to hierarchy users"""
        total_commission = self.calculate_commission(transaction_amount)
        
        distribution = {
            'admin': (total_commission * self.admin_commission) / 100,
            'master': (total_commission * self.master_commission) / 100,
            'dealer': (total_commission * self.dealer_commission) / 100,
            'retailer': (total_commission * self.retailer_commission) / 100,
        }
        
        hierarchy_users = self.get_commission_hierarchy(retailer_user)
        
        return distribution, hierarchy_users
    
    def get_commission_hierarchy(self, retailer_user):
        """Get all users in commission hierarchy for a retailer"""
        hierarchy = {
            'retailer': retailer_user,
            'dealer': retailer_user.created_by if retailer_user.created_by and retailer_user.created_by.role == 'dealer' else None,
            'master': None,
            'admin': None
        }
        
        if hierarchy['dealer']:
            hierarchy['master'] = hierarchy['dealer'].created_by if hierarchy['dealer'].created_by and hierarchy['dealer'].created_by.role == 'master' else None
        
        if hierarchy['master']:
            hierarchy['admin'] = hierarchy['master'].created_by if hierarchy['master'].created_by and hierarchy['master'].created_by.role in ['admin', 'superadmin'] else None
        
        if not hierarchy['admin']:
            hierarchy['admin'] = User.objects.filter(role__in=['admin', 'superadmin'], is_active=True).first()
        
        return hierarchy

class CommissionTransaction(models.Model):
    TRANSACTION_TYPES = (
        ('credit', 'Credit'),
        ('debit', 'Debit'),
    )
    
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('success', 'Success'),
        ('failed', 'Failed'),
    )
    
    main_transaction = models.ForeignKey('users.Transaction', on_delete=models.CASCADE, related_name='commission_transactions')
    service_submission = models.ForeignKey('services.ServiceSubmission', on_delete=models.CASCADE, null=True, blank=True)
    
    commission_config = models.ForeignKey(ServiceCommission, on_delete=models.CASCADE)
    commission_plan = models.ForeignKey(CommissionPlan, on_delete=models.CASCADE)
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='commission_earnings')
    role = models.CharField(max_length=20, choices=User.ROLE_CHOICES)
    commission_amount = models.DecimalField(max_digits=10, decimal_places=2)
    
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPES, default='credit')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='success')
    description = models.TextField()
    
    retailer_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='retailer_commissions'
    )
    original_transaction_amount = models.DecimalField(max_digits=10, decimal_places=2)
    
    reference_number = models.CharField(max_length=100, unique=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['retailer_user', 'created_at']),
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['role', 'created_at']),
        ]
    
    def __str__(self):
        return f"Commission - {self.user.username} - ₹{self.commission_amount}"
    
    def save(self, *args, **kwargs):
        if not self.reference_number:
            self.reference_number = self.generate_reference_number()
        super().save(*args, **kwargs)
    
    def generate_reference_number(self):
        """Generate unique reference number"""
        timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
        random_str = str(random.randint(1000, 9999))
        return f"COM{timestamp}{random_str}"

class UserCommissionPlan(models.Model):
    """Assign commission plans to users"""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='commission_plan')
    commission_plan = models.ForeignKey(CommissionPlan, on_delete=models.CASCADE)
    is_active = models.BooleanField(default=True)
    assigned_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='assigned_plans')
    assigned_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.commission_plan.name}"

class CommissionSettings(models.Model):
    """Global commission settings"""
    key = models.CharField(max_length=100, unique=True)
    value = models.JSONField()
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.key

class CommissionPayout(models.Model):
    PAYOUT_STATUS = (
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    )
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='commission_payouts')
    total_amount = models.DecimalField(max_digits=15, decimal_places=2)
    commission_period_start = models.DateField()
    commission_period_end = models.DateField()
    status = models.CharField(max_length=20, choices=PAYOUT_STATUS, default='pending')
    reference_number = models.CharField(max_length=100, unique=True, blank=True)
    
    payout_method = models.CharField(max_length=50, blank=True, null=True)
    payout_reference = models.CharField(max_length=100, blank=True, null=True)
    
    processed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='processed_payouts'
    )
    processed_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-commission_period_end']
    
    def __str__(self):
        return f"Payout - {self.user.username} - ₹{self.total_amount}"
    
    def save(self, *args, **kwargs):
        if not self.reference_number:
            self.reference_number = self.generate_reference_number()
        super().save(*args, **kwargs)
    
    def generate_reference_number(self):
        """Generate unique reference number"""
        timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
        random_str = str(random.randint(1000, 9999))
        return f"PAY{timestamp}{random_str}"