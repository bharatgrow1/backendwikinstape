from django.contrib.auth.models import AbstractUser, Permission
from django.db import models
from django.utils import timezone
from django.conf import settings
from datetime import timedelta
import random
from django.apps import apps
from django.contrib.contenttypes.models import ContentType

class User(AbstractUser):
    ROLE_CHOICES = (
        ('superadmin', 'Super Admin'),
        ('admin', 'Admin'),
        ('master', 'Master'),
        ('dealer', 'Dealer'),
        ('retailer', 'Retailer'),
    )

    GENDER_CHOICES = (
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
        ('prefer_not_to_say', 'Prefer not to say'),
    )
    
    BUSINESS_OWNERSHIP_CHOICES = (
        ('private', 'Private'),
        ('private_limited', 'Private Limited'),
        ('llc', 'Limited Liability Company (LLC)'),
        ('public_limited', 'Public Limited'),
        ('other', 'Other'),
    )
    
    BUSINESS_NATURE_CHOICES = (
        ('retail_shop', 'Retail Shop'),
        ('wholesale', 'Wholesale'),
        ('service_provider', 'Service Provider'),
        ('manufacturer', 'Manufacturer'),
        ('distributor', 'Distributor'),
        ('franchise', 'Franchise'),
        ('other', 'Other'),
    )

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='retailer')
    created_by = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_users'
    )

    # Personal Information
    first_name = models.CharField(max_length=30, blank=True, null=True)
    last_name = models.CharField(max_length=30, blank=True, null=True)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    alternative_phone = models.CharField(max_length=15, blank=True, null=True)
    aadhar_number = models.CharField(max_length=12, blank=True, null=True)
    pan_number = models.CharField(max_length=10, blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    gender = models.CharField(max_length=20, choices=GENDER_CHOICES, blank=True, null=True)
    services = models.ManyToManyField('services.ServiceSubCategory', through='UserService',related_name='users',blank=True)
    business_name = models.CharField(max_length=255, blank=True, null=True)
    business_nature = models.CharField(max_length=50, choices=BUSINESS_NATURE_CHOICES, blank=True, null=True)
    business_registration_number = models.CharField(max_length=50, blank=True, null=True)
    gst_number = models.CharField(max_length=15, blank=True, null=True)
    business_ownership_type = models.CharField(max_length=20, choices=BUSINESS_OWNERSHIP_CHOICES, blank=True, null=True)
    
    # Address Information
    address = models.TextField(blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    state = models.CharField(max_length=100, blank=True, null=True)
    pincode = models.CharField(max_length=10, blank=True, null=True)
    landmark = models.CharField(max_length=255, blank=True, null=True)
    
    # Bank Information
    bank_name = models.CharField(max_length=255, blank=True, null=True)
    account_number = models.CharField(max_length=50, blank=True, null=True)
    ifsc_code = models.CharField(max_length=11, blank=True, null=True)
    account_holder_name = models.CharField(max_length=255, blank=True, null=True)
    
    # Document Uploads (store file paths)
    pan_card = models.FileField(upload_to='documents/pan/', blank=True, null=True)
    aadhar_card = models.FileField(upload_to='documents/aadhar/', blank=True, null=True)
    passport_photo = models.FileField(upload_to='documents/passport/', blank=True, null=True)
    shop_photo = models.FileField(upload_to='documents/shop/', blank=True, null=True)
    store_photo = models.FileField(upload_to='documents/store/', blank=True, null=True)
    other_documents = models.FileField(upload_to='documents/other/', blank=True, null=True)

    def __str__(self):
        return f"{self.username} ({self.role})"
    
    def is_admin_user(self):
        """Check if user is admin, superadmin or master"""
        return self.role in ["admin", "superadmin", "master"]
    
    def has_perm(self, perm, obj=None):
        """Override has_perm to use our permission system"""
        if self.role == 'superadmin':
            return True
        return self.has_permission(perm)
    
    def has_module_perms(self, app_label):
        """Override has_module_perms"""
        if self.role == 'superadmin':
            return True
        return super().has_module_perms(app_label)
    
    def has_permission(self, perm_codename):
        """Check if user has specific permission"""
        # Super Admin and Master have all permissions
        if self.role in ['superadmin', 'master']:
            return True
            
        # Check user-specific permissions
        return self.user_permissions.filter(codename=perm_codename).exists()
    
    def has_model_permission(self, model, action):
        """Check if user has specific model permission (view, add, change, delete)"""
        if self.role in ['superadmin', 'master']:
            return True
            
        permission_codename = f"{action}_{model._meta.model_name}"
        return self.has_permission(permission_codename)
    
    def get_model_permissions(self, model):
        """Get all permissions user has for a specific model"""
        if self.role in ['superadmin', 'master']:
            return {'view': True, 'add': True, 'change': True, 'delete': True}
        
        model_name = model._meta.model_name
        user_permissions = self.user_permissions.filter(
            content_type__app_label=model._meta.app_label,
            content_type__model=model_name
        ).values_list('codename', flat=True)
        
        return {
            'view': f'view_{model_name}' in user_permissions,
            'add': f'add_{model_name}' in user_permissions,
            'change': f'change_{model_name}' in user_permissions,
            'delete': f'delete_{model_name}' in user_permissions,
        }
    
    def can_view_model(self, model):
        return self.has_model_permission(model, 'view')
    
    def can_add_model(self, model):
        return self.has_model_permission(model, 'add')
    
    def can_change_model(self, model):
        return self.has_model_permission(model, 'change')
    
    def can_delete_model(self, model):
        return self.has_model_permission(model, 'delete')
    
    def can_manage_users(self):
        return self.role in ['superadmin', 'master', 'admin']
    
    def can_manage_balance_requests(self):
        return self.role in ['superadmin', 'master', 'admin']
    

    def can_create_user_with_role(self, target_role):
        """Check if user can create another user with specific role"""
        role_hierarchy = {
            'superadmin': ['superadmin', 'admin', 'master', 'dealer', 'retailer'],
            'admin': ['admin', 'master', 'dealer', 'retailer'],
            'master': ['master', 'dealer', 'retailer'],
            'dealer': ['retailer'],
            'retailer': []
        }
        
        if self.role not in role_hierarchy:
            return False
            
        return target_role in role_hierarchy[self.role]
    


class UserService(models.Model):
    """Model to store user selected services"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_services')
    service = models.ForeignKey('services.ServiceSubCategory', on_delete=models.CASCADE, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['user', 'service']
        ordering = ['-created_at']

    def __str__(self):
        service_name = self.service.name if self.service else "Deleted Service"
        return f"{self.user.username} - {service_name}"
    

class State(models.Model):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=10)

    def __str__(self):
        return self.name

class City(models.Model):
    state = models.ForeignKey(State, on_delete=models.CASCADE, related_name='cities')
    name = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.name}, {self.state.name}"

class RolePermission(models.Model):
    """Permissions assigned to specific roles"""
    role = models.CharField(max_length=20, choices=User.ROLE_CHOICES)
    permission = models.ForeignKey(Permission, on_delete=models.CASCADE)
    granted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='granted_role_permissions'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['role', 'permission']

    def __str__(self):
        return f"{self.role} - {self.permission.codename}"

class EmailOTP(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    otp = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)

    def generate_otp(self):
        self.otp = str(random.randint(100000, 999999))
        self.created_at = timezone.now()
        self.save()
        return self.otp

    def is_expired(self):
        return timezone.now() > self.created_at + timedelta(minutes=5)

class Wallet(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="wallet")
    balance = models.DecimalField(max_digits=15, decimal_places=2, default=0.00)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}'s Wallet - ${self.balance}"

class BalanceRequest(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    )
    
    retailer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='balance_requests',
        limit_choices_to={'role': 'retailer'}
    )
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    description = models.TextField(blank=True)
    admin_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    processed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='processed_requests'
    )

    def __str__(self):
        return f"{self.retailer.username} - ${self.amount} - {self.status}"

class Transaction(models.Model):
    TRANSACTION_TYPES = (
        ('credit', 'Credit'),
        ('debit', 'Debit'),
    )
    
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name='transactions')
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPES)
    description = models.CharField(max_length=255)
    balance_request = models.ForeignKey(BalanceRequest, on_delete=models.SET_NULL, null=True, blank=True, related_name='transactions')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='created_transactions')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.transaction_type} - ${self.amount} - {self.wallet.user.username}"
    



class ForgotPasswordOTP(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    otp = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)

    def generate_otp(self):
        self.otp = str(random.randint(100000, 999999))
        self.created_at = timezone.now()
        self.is_used = False
        self.save()
        return self.otp

    def is_expired(self):
        return timezone.now() > self.created_at + timedelta(minutes=10)

    def mark_used(self):
        self.is_used = True
        self.save()