from django.db import models
from django.conf import settings
import uuid
#from datetime import timezone
from django.utils import timezone


class UploadImage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    image = models.ImageField(upload_to='service_images/')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Image {self.id}"

class ServiceCategory(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    icon = models.CharField(max_length=500, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Service Categories"
        ordering = ['created_at']

    def __str__(self):
        return self.name

class ServiceSubCategory(models.Model):
    category = models.ForeignKey(ServiceCategory, on_delete=models.CASCADE, related_name='subcategories')
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    image = models.CharField(max_length=500, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    
    # Boolean fields for each possible form field
    # Personal Information
    require_customer_name = models.BooleanField(default=False)
    require_customer_email = models.BooleanField(default=False)
    require_customer_phone = models.BooleanField(default=False)
    require_customer_address = models.BooleanField(default=False)
    
    # Service Specific Fields
    require_mobile_number = models.BooleanField(default=False)
    require_consumer_number = models.BooleanField(default=False)
    require_account_number = models.BooleanField(default=False)
    require_bill_number = models.BooleanField(default=False)
    require_transaction_id = models.BooleanField(default=False)
    require_reference_number = models.BooleanField(default=False)
    
    # Location Fields
    require_state = models.BooleanField(default=False)
    require_city = models.BooleanField(default=False)
    require_pincode = models.BooleanField(default=False)
    
    # Amount Fields
    require_amount = models.BooleanField(default=False)
    require_tax_amount = models.BooleanField(default=False)
    require_total_amount = models.BooleanField(default=False)
    
    # Service Provider Fields
    require_service_provider = models.BooleanField(default=False)
    require_operator = models.BooleanField(default=False)
    require_biller = models.BooleanField(default=False)
    require_bank_name = models.BooleanField(default=False)
    
    # Vehicle Fields (for Fastag, Traffic Challan)
    require_vehicle_number = models.BooleanField(default=False)
    require_vehicle_type = models.BooleanField(default=False)
    require_rc_number = models.BooleanField(default=False)
    
    # Education Fields
    require_student_name = models.BooleanField(default=False)
    require_student_id = models.BooleanField(default=False)
    require_institute_name = models.BooleanField(default=False)
    require_course_name = models.BooleanField(default=False)
    
    # Loan Fields
    require_loan_type = models.BooleanField(default=False)
    require_loan_account_number = models.BooleanField(default=False)
    require_emi_amount = models.BooleanField(default=False)
    
    # OTT/Subscription Fields
    require_ott_platform = models.BooleanField(default=False)
    require_subscription_plan = models.BooleanField(default=False)
    require_validity = models.BooleanField(default=False)
    
    # Utility Fields
    require_meter_number = models.BooleanField(default=False)
    require_connection_type = models.BooleanField(default=False)
    require_usage_amount = models.BooleanField(default=False)
    
    # Payment Fields
    require_payment_method = models.BooleanField(default=False)
    require_card_number = models.BooleanField(default=False)
    require_card_holder_name = models.BooleanField(default=False)
    require_expiry_date = models.BooleanField(default=False)
    require_cvv = models.BooleanField(default=False)
    
    # Additional Fields
    require_due_date = models.BooleanField(default=False)
    require_billing_period = models.BooleanField(default=False)
    require_remarks = models.BooleanField(default=False)
    require_documents = models.BooleanField(default=False)
    
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Service Sub Categories"
        ordering = ['created_at']

    def __str__(self):
        return f"{self.category.name} - {self.name}"
    
    def get_required_fields(self):
        """Get all required fields for this service"""
        fields = []
        boolean_fields = [
            # Personal Information
            ('require_customer_name', 'customer_name', 'text', 'Customer Name'),
            ('require_customer_email', 'customer_email', 'email', 'Customer Email'),
            ('require_customer_phone', 'customer_phone', 'phone', 'Customer Phone'),
            ('require_customer_address', 'customer_address', 'textarea', 'Customer Address'),
            
            # Service Specific
            ('require_mobile_number', 'mobile_number', 'phone', 'Mobile Number'),
            ('require_consumer_number', 'consumer_number', 'text', 'Consumer Number'),
            ('require_account_number', 'account_number', 'text', 'Account Number'),
            ('require_bill_number', 'bill_number', 'text', 'Bill Number'),
            ('require_transaction_id', 'transaction_id', 'text', 'Transaction ID'),
            ('require_reference_number', 'reference_number', 'text', 'Reference Number'),
            
            # Location
            ('require_state', 'state', 'select', 'State'),
            ('require_city', 'city', 'select', 'City'),
            ('require_pincode', 'pincode', 'text', 'Pincode'),
            
            # Amount
            ('require_amount', 'amount', 'amount', 'Amount'),
            ('require_tax_amount', 'tax_amount', 'amount', 'Tax Amount'),
            ('require_total_amount', 'total_amount', 'amount', 'Total Amount'),
            
            # Service Provider
            ('require_service_provider', 'service_provider', 'select', 'Service Provider'),
            ('require_operator', 'operator', 'select', 'Operator'),
            ('require_biller', 'biller', 'select', 'Biller'),
            ('require_bank_name', 'bank_name', 'select', 'Bank Name'),
            
            # Vehicle
            ('require_vehicle_number', 'vehicle_number', 'text', 'Vehicle Number'),
            ('require_vehicle_type', 'vehicle_type', 'select', 'Vehicle Type'),
            ('require_rc_number', 'rc_number', 'text', 'RC Number'),
            
            # Education
            ('require_student_name', 'student_name', 'text', 'Student Name'),
            ('require_student_id', 'student_id', 'text', 'Student ID'),
            ('require_institute_name', 'institute_name', 'select', 'Institute Name'),
            ('require_course_name', 'course_name', 'text', 'Course Name'),
            
            # Loan
            ('require_loan_type', 'loan_type', 'select', 'Loan Type'),
            ('require_loan_account_number', 'loan_account_number', 'text', 'Loan Account Number'),
            ('require_emi_amount', 'emi_amount', 'amount', 'EMI Amount'),
            
            # OTT
            ('require_ott_platform', 'ott_platform', 'select', 'OTT Platform'),
            ('require_subscription_plan', 'subscription_plan', 'select', 'Subscription Plan'),
            ('require_validity', 'validity', 'select', 'Validity'),
            
            # Utility
            ('require_meter_number', 'meter_number', 'text', 'Meter Number'),
            ('require_connection_type', 'connection_type', 'select', 'Connection Type'),
            ('require_usage_amount', 'usage_amount', 'amount', 'Usage Amount'),
            
            # Payment
            ('require_payment_method', 'payment_method', 'select', 'Payment Method'),
            ('require_card_number', 'card_number', 'text', 'Card Number'),
            ('require_card_holder_name', 'card_holder_name', 'text', 'Card Holder Name'),
            ('require_expiry_date', 'expiry_date', 'date', 'Expiry Date'),
            ('require_cvv', 'cvv', 'text', 'CVV'),
            
            # Additional
            ('require_due_date', 'due_date', 'date', 'Due Date'),
            ('require_billing_period', 'billing_period', 'text', 'Billing Period'),
            ('require_remarks', 'remarks', 'textarea', 'Remarks'),
            ('require_documents', 'documents', 'file', 'Documents'),
        ]
        
        for bool_field, field_name, field_type, field_label in boolean_fields:
            if getattr(self, bool_field):
                fields.append({
                    'field_name': field_name,
                    'field_label': field_label,
                    'field_type': field_type,
                    'required': True
                })
        
        return fields

class ServiceForm(models.Model):
    FIELD_TYPES = [
        ('text', 'Text Input'),
        ('number', 'Number Input'),
        ('email', 'Email Input'),
        ('phone', 'Phone Input'),
        ('textarea', 'Text Area'),
        ('boolean', 'Checkbox'),
        ('select', 'Dropdown'),
        ('multiselect', 'Multiple Select'),
        ('date', 'Date Picker'),
        ('file', 'File Upload'),
        ('radio', 'Radio Buttons'),
        ('amount', 'Amount'),
        ('operator', 'Operator'),
        ('circle', 'Circle'),
        ('plan_type', 'Plan Type'),
        ('recharge_type', 'Recharge Type'),
    ]

    SERVICE_TYPES = [
        ('mobile_recharge', 'Mobile Recharge'),
        ('dtm', 'DTM Service'),
        ('electricity', 'Electricity Bill'),
        ('water', 'Water Bill'),
        ('gas', 'Gas Bill'),
        ('insurance', 'Insurance'),
        ('loan', 'Loan Service'),
        ('booking', 'Booking Service'),
        ('other', 'Other Service'),
    ]

    service_type = models.CharField(max_length=50, choices=SERVICE_TYPES)
    service_subcategory = models.ForeignKey(
        'ServiceSubCategory', 
        on_delete=models.CASCADE,
        related_name='service_forms'
    )
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    
    # Form Configuration
    is_active = models.BooleanField(default=True)
    requires_approval = models.BooleanField(default=False)
    max_submissions_per_user = models.IntegerField(default=0)
    
    # Metadata
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = "Service Form"
        verbose_name_plural = "Service Forms"

    def __str__(self):
        return f"{self.get_service_type_display()} - {self.name}"

class FormField(models.Model):
    SERVICE_SPECIFIC_OPTIONS = {
        'operator': [
            'Airtel', 'Jio', 'Vi (Vodafone Idea)', 'BSNL', 'MTNL',
            'Airtel Prepaid', 'Airtel Postpaid', 'Jio Prepaid', 'Jio Postpaid',
            'Vi Prepaid', 'Vi Postpaid', 'BSNL Prepaid', 'BSNL Postpaid'
        ],
        'circle': [
            'Andhra Pradesh', 'Assam', 'Bihar', 'Chennai', 'Delhi NCR',
            'Gujarat', 'Haryana', 'Himachal Pradesh', 'Jammu & Kashmir',
            'Karnataka', 'Kerala', 'Kolkata', 'Maharashtra', 'Mumbai',
            'North East', 'Odisha', 'Punjab', 'Rajasthan', 'Tamil Nadu',
            'Telangana', 'Uttar Pradesh (East)', 'Uttar Pradesh (West)',
            'West Bengal', 'Other'
        ],
        'plan_type': [
            'Full Talktime', 'Top-up', 'Special', 'Data', 'Combo',
            'ROM', 'STV', 'SMS', 'International', 'ISD'
        ],
        'recharge_type': [
            'Prepaid', 'Postpaid', '2G', '3G', '4G', '5G'
        ]
    }

    form = models.ForeignKey(ServiceForm, on_delete=models.CASCADE, related_name='fields')
    
    # Field Identification
    field_id = models.CharField(max_length=100, unique=True)
    field_name = models.CharField(max_length=100)
    field_label = models.CharField(max_length=200)
    field_type = models.CharField(max_length=20, choices=ServiceForm.FIELD_TYPES)
    
    # Field Properties
    required = models.BooleanField(default=False)
    readonly = models.BooleanField(default=False)
    hidden = models.BooleanField(default=False)
    
    # UI Properties
    placeholder = models.CharField(max_length=200, blank=True, null=True)
    help_text = models.TextField(blank=True, null=True)
    css_class = models.CharField(max_length=100, blank=True, null=True)
    
    # Validation
    min_value = models.IntegerField(blank=True, null=True)
    max_value = models.IntegerField(blank=True, null=True)
    min_length = models.IntegerField(blank=True, null=True)
    max_length = models.IntegerField(blank=True, null=True)
    validation_regex = models.CharField(max_length=500, blank=True, null=True)
    error_message = models.CharField(max_length=200, blank=True, null=True)
    
    # Options for select fields
    options = models.JSONField(blank=True, null=True)
    use_service_options = models.CharField(max_length=50, blank=True, null=True)
    
    # Order and Grouping
    order = models.IntegerField(default=0)
    group = models.CharField(max_length=100, blank=True, null=True)
    
    # Conditional Logic
    depends_on = models.CharField(max_length=100, blank=True, null=True)
    condition_value = models.CharField(max_length=200, blank=True, null=True)
    condition_type = models.CharField(max_length=20, default='equals', choices=[
        ('equals', 'Equals'),
        ('not_equals', 'Not Equals'),
        ('contains', 'Contains'),
        ('greater_than', 'Greater Than'),
        ('less_than', 'Less Than'),
    ])
    
    # Status
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', 'id']
        unique_together = ['form', 'field_id']

    def save(self, *args, **kwargs):
        if not self.field_id:
            self.field_id = f"{self.form.id}_{self.field_name}_{uuid.uuid4().hex[:8]}"
        
        # Auto-populate options for service-specific fields
        if self.use_service_options and self.use_service_options in self.SERVICE_SPECIFIC_OPTIONS:
            self.options = self.SERVICE_SPECIFIC_OPTIONS[self.use_service_options]
        
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.form.name} - {self.field_label}"

class ServiceSubmission(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('processing', 'Processing'),
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]

    PAYMENT_STATUS = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]

    # Submission Info
    submission_id = models.CharField(max_length=50, unique=True, blank=True)
    service_form = models.ForeignKey(ServiceForm, on_delete=models.CASCADE)
    service_subcategory = models.ForeignKey('ServiceSubCategory', on_delete=models.CASCADE)
    
    # User Information
    submitted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    customer_name = models.CharField(max_length=200, blank=True, null=True)
    customer_email = models.EmailField(blank=True, null=True)
    customer_phone = models.CharField(max_length=15, blank=True, null=True)
    
    # Form Data
    form_data = models.JSONField()  # Store all form field values
    
    # Status Tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='pending')
    
    # Amount and Payment
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    transaction_id = models.CharField(max_length=100, blank=True, null=True)
    payment_gateway_response = models.JSONField(blank=True, null=True)
    
    # Service Response
    service_response = models.JSONField(blank=True, null=True)
    service_reference_id = models.CharField(max_length=100, blank=True, null=True)
    
    # Additional Info
    notes = models.TextField(blank=True, null=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField(blank=True, null=True)
    
    # Timestamps
    submitted_at = models.DateTimeField(blank=True, null=True)
    processed_at = models.DateTimeField(blank=True, null=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['submission_id']),
            models.Index(fields=['status']),
            models.Index(fields=['submitted_by', 'created_at']),
        ]

    def save(self, *args, **kwargs):
        if not self.submission_id:
            self.submission_id = f"SUB{uuid.uuid4().hex[:12].upper()}"
        
        if self.status == 'submitted' and not self.submitted_at:
            self.submitted_at = timezone.now()
        
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.submission_id} - {self.service_form.name}"

class FormSubmissionFile(models.Model):
    submission = models.ForeignKey(ServiceSubmission, on_delete=models.CASCADE, related_name='files')
    field_name = models.CharField(max_length=100)
    file = models.FileField(upload_to='service_submissions/%Y/%m/%d/')
    original_filename = models.CharField(max_length=255)
    file_size = models.IntegerField()
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.submission.submission_id} - {self.field_name}"
