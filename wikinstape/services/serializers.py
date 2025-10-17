from rest_framework import serializers
from .models import (ServiceCategory, ServiceSubCategory, ServiceForm, FormField, ServiceSubmission, 
                     FormSubmissionFile )

class ServiceSubCategorySerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    
    class Meta:
        model = ServiceSubCategory
        fields = ['id', 'category', 'category_name', 'name', 'description', 'is_active', 'created_at']

class ServiceCategorySerializer(serializers.ModelSerializer):
    subcategories = ServiceSubCategorySerializer(many=True, read_only=True)
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    
    class Meta:
        model = ServiceCategory
        fields = ['id', 'name', 'description', 'icon', 'is_active', 'subcategories', 'created_by', 'created_by_username', 'created_at', 'updated_at']




class FormFieldSerializer(serializers.ModelSerializer):
    class Meta:
        model = FormField
        fields = [
            'id', 'field_id', 'field_name', 'field_label', 'field_type', 
            'required', 'readonly', 'hidden', 'placeholder', 'help_text',
            'css_class', 'min_value', 'max_value', 'min_length', 'max_length',
            'validation_regex', 'error_message', 'options', 'use_service_options',
            'order', 'group', 'depends_on', 'condition_value', 'condition_type',
            'is_active'
        ]

class ServiceFormSerializer(serializers.ModelSerializer):
    fields = FormFieldSerializer(many=True, read_only=True)
    service_subcategory_name = serializers.CharField(source='service_subcategory.name', read_only=True)
    service_category_name = serializers.CharField(source='service_subcategory.category.name', read_only=True)
    
    class Meta:
        model = ServiceForm
        fields = [
            'id', 'service_type', 'service_subcategory', 'service_subcategory_name',
            'service_category_name', 'name', 'description', 'is_active',
            'requires_approval', 'max_submissions_per_user', 'fields',
            'created_at', 'updated_at'
        ]

class FormSubmissionFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = FormSubmissionFile
        fields = ['id', 'field_name', 'file', 'original_filename', 'file_size', 'uploaded_at']

class ServiceSubmissionSerializer(serializers.ModelSerializer):
    service_form_name = serializers.CharField(source='service_form.name', read_only=True)
    service_subcategory_name = serializers.CharField(source='service_subcategory.name', read_only=True)
    submitted_by_username = serializers.CharField(source='submitted_by.username', read_only=True)
    files = FormSubmissionFileSerializer(many=True, read_only=True)
    
    class Meta:
        model = ServiceSubmission
        fields = [
            'id', 'submission_id', 'service_form', 'service_form_name',
            'service_subcategory', 'service_subcategory_name', 'submitted_by',
            'submitted_by_username', 'customer_name', 'customer_email',
            'customer_phone', 'form_data', 'status', 'payment_status',
            'amount', 'transaction_id', 'service_response',
            'service_reference_id', 'notes', 'files', 'submitted_at',
            'processed_at', 'completed_at', 'created_at', 'updated_at'
        ]
        read_only_fields = ['submission_id', 'submitted_at', 'processed_at', 'completed_at']

class DynamicFormSubmissionSerializer(serializers.Serializer):
    def __init__(self, *args, **kwargs):
        self.form_fields = kwargs.pop('form_fields', [])
        super().__init__(*args, **kwargs)
        
        # Dynamically add fields based on form configuration
        for field in self.form_fields:
            field_name = field.field_name
            
            if field.field_type == 'text':
                self.fields[field_name] = serializers.CharField(
                    required=field.required,
                    allow_blank=not field.required,
                    max_length=field.max_length,
                    help_text=field.help_text
                )
            elif field.field_type == 'number':
                self.fields[field_name] = serializers.IntegerField(
                    required=field.required,
                    min_value=field.min_value,
                    max_value=field.max_value,
                    help_text=field.help_text
                )
            elif field.field_type == 'email':
                self.fields[field_name] = serializers.EmailField(
                    required=field.required,
                    allow_blank=not field.required,
                    help_text=field.help_text
                )
            elif field.field_type == 'phone':
                self.fields[field_name] = serializers.CharField(
                    required=field.required,
                    allow_blank=not field.required,
                    max_length=15,
                    help_text=field.help_text
                )
            elif field.field_type == 'boolean':
                self.fields[field_name] = serializers.BooleanField(
                    required=field.required,
                    help_text=field.help_text
                )
            elif field.field_type in ['select', 'radio']:
                choices = [(opt, opt) for opt in (field.options or [])]
                self.fields[field_name] = serializers.ChoiceField(
                    choices=choices,
                    required=field.required,
                    help_text=field.help_text
                )
            elif field.field_type == 'multiselect':
                choices = [(opt, opt) for opt in (field.options or [])]
                self.fields[field_name] = serializers.MultipleChoiceField(
                    choices=choices,
                    required=field.required,
                    help_text=field.help_text
                )
            elif field.field_type == 'date':
                self.fields[field_name] = serializers.DateField(
                    required=field.required,
                    help_text=field.help_text
                )
            elif field.field_type == 'textarea':
                self.fields[field_name] = serializers.CharField(
                    required=field.required,
                    allow_blank=not field.required,
                    help_text=field.help_text,
                    style={'base_template': 'textarea.html'}
                )
            elif field.field_type == 'amount':
                self.fields[field_name] = serializers.DecimalField(
                    required=field.required,
                    max_digits=10,
                    decimal_places=2,
                    min_value=field.min_value,
                    max_value=field.max_value,
                    help_text=field.help_text
                )

class ServiceFormWithFieldsSerializer(serializers.ModelSerializer):
    fields = FormFieldSerializer(many=True, read_only=True)
    
    class Meta:
        model = ServiceForm
        fields = ['id', 'name', 'description', 'service_type', 'fields']