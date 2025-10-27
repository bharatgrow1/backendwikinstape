from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from django.db import transaction
import uuid
from django.shortcuts import get_object_or_404
from rest_framework.permissions import AllowAny
from rest_framework.decorators import api_view, permission_classes, parser_classes

from .models import (
    ServiceCategory, ServiceSubCategory, ServiceForm, FormField, ServiceSubmission, FormSubmissionFile, UploadImage
)
from .serializers import (
    ServiceCategorySerializer, ServiceSubCategorySerializer, ServiceFormSerializer,
    ServiceSubmissionSerializer, DynamicFormSubmissionSerializer, ServiceFormWithFieldsSerializer, 
    UploadImageSerializer, DirectServiceFormSerializer, ServiceCategoryWithFormsSerializer
)

# -------------------------------
# Service Category ViewSet
# -------------------------------
class ServiceCategoryViewSet(viewsets.ModelViewSet):
    permission_classes = [AllowAny]
    queryset = ServiceCategory.objects.all()
    serializer_class = ServiceCategorySerializer

    def get_queryset(self):
        return ServiceCategory.objects.all().order_by('created_at')

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

# -------------------------------
# Direct Service Form ViewSet  
# -------------------------------
class DirectServiceFormViewSet(viewsets.ModelViewSet):
    permission_classes = [AllowAny]
    queryset = ServiceForm.objects.filter(service_subcategory__isnull=True)
    serializer_class = DirectServiceFormSerializer

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_category_form_config(request, category_id):
    """Get form configuration based on category boolean fields"""
    try:
        category = ServiceCategory.objects.get(id=category_id)
        
        config = {
            'name': category.name,
            'description': category.description,
            'allow_direct_service': category.allow_direct_service,
            'fields': category.get_required_fields()
        }
        
        return Response(config)
        
    except ServiceCategory.DoesNotExist:
        return Response({'error': 'Category not found'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['POST'])
@permission_classes([AllowAny])
def copy_category_fields_to_subcategory(request):
    """Copy all boolean fields from category to subcategory"""
    category_id = request.data.get('category_id')
    subcategory_id = request.data.get('subcategory_id')
    
    if not category_id or not subcategory_id:
        return Response({'error': 'category_id and subcategory_id are required'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        category = ServiceCategory.objects.get(id=category_id)
        subcategory = ServiceSubCategory.objects.get(id=subcategory_id)
        
        # Copy boolean fields
        category.copy_boolean_fields_to_subcategory(subcategory)
        
        serializer = ServiceSubCategorySerializer(subcategory)
        return Response({
            'message': 'Boolean fields copied successfully',
            'subcategory': serializer.data
        })
        
    except ServiceCategory.DoesNotExist:
        return Response({'error': 'Category not found'}, status=status.HTTP_404_NOT_FOUND)
    except ServiceSubCategory.DoesNotExist:
        return Response({'error': 'Subcategory not found'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['POST'])
@permission_classes([AllowAny])
def create_direct_category_form(request):
    """Create form directly for service category using its boolean fields"""
    category_id = request.data.get('category_id')
    form_name = request.data.get('name')
    form_description = request.data.get('description', '')
    
    if not category_id or not form_name:
        return Response({'error': 'category_id and name are required'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        category = ServiceCategory.objects.get(id=category_id)
        
        if not category.allow_direct_service:
            return Response({'error': 'This category does not allow direct services'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Create service form directly for category
        service_form = ServiceForm.objects.create(
            service_type='direct_category',
            service_category=category,
            service_subcategory=None,  # Direct form, no subcategory
            name=form_name,
            description=form_description,
            created_by=request.user
        )
        
        # Create form fields based on category's boolean flags
        required_fields = category.get_required_fields()
        for index, field_config in enumerate(required_fields):
            FormField.objects.create(
                form=service_form,
                field_id=f"category_{category.id}_{field_config['field_name']}_{uuid.uuid4().hex[:8]}",
                field_name=field_config['field_name'],
                field_label=field_config['field_label'],
                field_type=field_config['field_type'],
                required=field_config.get('required', True),
                order=index,
                is_active=True
            )
        
        serializer = ServiceFormWithFieldsSerializer(service_form)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
        
    except ServiceCategory.DoesNotExist:
        return Response({'error': 'Category not found'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['GET'])
@permission_classes([AllowAny])
def get_categories_with_direct_services(request):
    """Get all categories that allow direct services"""
    categories = ServiceCategory.objects.filter(allow_direct_service=True, is_active=True)
    serializer = ServiceCategoryWithFormsSerializer(categories, many=True)
    return Response(serializer.data)


# -------------------------------
# Service SubCategory ViewSet
# -------------------------------
class ServiceSubCategoryViewSet(viewsets.ModelViewSet):
    permission_classes = [AllowAny]
    queryset = ServiceSubCategory.objects.all()
    serializer_class = ServiceSubCategorySerializer

    def get_queryset(self):
        queryset = ServiceSubCategory.objects.all().order_by('created_at')
        category_id = self.request.query_params.get('category_id')
        if category_id:
            queryset = queryset.filter(category_id=category_id)
        return queryset

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=False, methods=['get'])
    def by_category(self, request):
        category_id = request.query_params.get('category_id')
        if not category_id:
            return Response({'error': 'category_id parameter is required'}, status=status.HTTP_400_BAD_REQUEST)
        subcategories = ServiceSubCategory.objects.filter(category_id=category_id)
        serializer = self.get_serializer(subcategories, many=True)
        return Response(serializer.data)

# -------------------------------
# Service Form ViewSet
# -------------------------------
class ServiceFormViewSet(viewsets.ModelViewSet):
    permission_classes = [AllowAny]
    queryset = ServiceForm.objects.all()
    serializer_class = ServiceFormSerializer

    def get_queryset(self):
        queryset = ServiceForm.objects.all()
        service_type = self.request.query_params.get('service_type')
        subcategory_id = self.request.query_params.get('subcategory_id')
        if service_type:
            queryset = queryset.filter(service_type=service_type)
        if subcategory_id:
            queryset = queryset.filter(service_subcategory_id=subcategory_id)
        return queryset

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=['get'])
    def form_config(self, request, pk=None):
        service_form = self.get_object()
        serializer = ServiceFormWithFieldsSerializer(service_form)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def by_service_type(self, request):
        service_type = request.query_params.get('service_type')
        if not service_type:
            return Response({'error': 'service_type parameter is required'}, status=status.HTTP_400_BAD_REQUEST)
        forms = self.get_queryset().filter(service_type=service_type)
        serializer = self.get_serializer(forms, many=True)
        return Response(serializer.data)

# -------------------------------
# Service Submission ViewSet
# -------------------------------
class ServiceSubmissionViewSet(viewsets.ModelViewSet):
    permission_classes = [AllowAny]
    queryset = ServiceSubmission.objects.all()
    serializer_class = ServiceSubmissionSerializer
    parser_classes = [MultiPartParser, FormParser]

    def get_queryset(self):
        queryset = ServiceSubmission.objects.all()
        form_id = self.request.query_params.get('form_id')
        service_type = self.request.query_params.get('service_type')
        if form_id:
            queryset = queryset.filter(service_form_id=form_id)
        if service_type:
            queryset = queryset.filter(service_form__service_type=service_type)
        return queryset

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        form_id = request.data.get('service_form')
        service_form = get_object_or_404(ServiceForm, id=form_id)

        # Get form fields
        form_fields = service_form.fields.all().order_by('order')
        form_data = {}
        files_to_save = {}

        for field in form_fields:
            if field.field_name in request.data:
                form_data[field.field_name] = request.data[field.field_name]
            elif field.field_name in request.FILES:
                files_to_save[field.field_name] = request.FILES[field.field_name]

        # Validate form data
        dynamic_serializer = DynamicFormSubmissionSerializer(data=form_data, form_fields=form_fields)
        if not dynamic_serializer.is_valid():
            return Response({'errors': dynamic_serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        # Create submission
        submission_data = {
            'service_form': service_form.id,
            'service_subcategory': service_form.service_subcategory.id,
            'form_data': dynamic_serializer.validated_data,
            'status': 'submitted',
            'amount': request.data.get('amount', 0),
            'customer_name': request.data.get('customer_name'),
            'customer_email': request.data.get('customer_email'),
            'customer_phone': request.data.get('customer_phone'),
            'notes': request.data.get('notes')
        }

        serializer = self.get_serializer(data=submission_data)
        serializer.is_valid(raise_exception=True)
        submission = serializer.save()

        # Save files
        for field_name, file_obj in files_to_save.items():
            FormSubmissionFile.objects.create(
                submission=submission,
                field_name=field_name,
                file=file_obj,
                original_filename=file_obj.name,
                file_size=file_obj.size
            )

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def update_status(self, request, pk=None):
        submission = self.get_object()
        new_status = request.data.get('status')
        if new_status not in dict(ServiceSubmission.STATUS_CHOICES):
            return Response({'error': 'Invalid status'}, status=status.HTTP_400_BAD_REQUEST)
        submission.status = new_status
        submission.save()
        serializer = self.get_serializer(submission)
        return Response(serializer.data)

class ServiceImageViewSet(viewsets.ModelViewSet):
    queryset = UploadImage.objects.all()
    serializer_class = UploadImageSerializer
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

# New API Views for Boolean Fields System
@api_view(['GET'])
@permission_classes([AllowAny])
def get_subcategory_form_config(request, subcategory_id):
    """Get form configuration based on boolean fields"""
    try:
        subcategory = ServiceSubCategory.objects.get(id=subcategory_id)
        
        config = {
            'name': subcategory.name,
            'description': subcategory.description,
            'fields': subcategory.get_required_fields()
        }
        
        return Response(config)
        
    except ServiceSubCategory.DoesNotExist:
        return Response({'error': 'Subcategory not found'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['POST'])
@permission_classes([AllowAny])
def create_form_from_boolean_fields(request):
    """Create form based on boolean field configuration"""
    subcategory_id = request.data.get('subcategory_id')
    
    if not subcategory_id:
        return Response({'error': 'subcategory_id is required'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        subcategory = ServiceSubCategory.objects.get(id=subcategory_id)
        
        # Create service form
        service_form = ServiceForm.objects.create(
            service_type='custom',
            service_subcategory=subcategory,
            name=subcategory.name,
            description=subcategory.description or f"Form for {subcategory.name}",
            created_by=request.user
        )
        
        # Create form fields based on boolean flags
        required_fields = subcategory.get_required_fields()
        for field_config in required_fields:
            FormField.objects.create(
                form=service_form,
                field_id=f"{subcategory.id}_{field_config['field_name']}",
                field_name=field_config['field_name'],
                field_label=field_config['field_label'],
                field_type=field_config['field_type'],
                required=field_config.get('required', True),
                order=len(required_fields) - required_fields.index(field_config),
                is_active=True
            )
        
        serializer = ServiceFormWithFieldsSerializer(service_form)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
        
    except ServiceSubCategory.DoesNotExist:
        return Response({'error': 'Subcategory not found'}, status=status.HTTP_404_NOT_FOUND)
    



@api_view(['POST'])
@permission_classes([AllowAny])
@parser_classes([MultiPartParser, FormParser])
def create_service_submission_direct(request):
    """Create service submission directly without needing ServiceForm"""
    try:
        subcategory_id = request.data.get('service_subcategory')
        
        if not subcategory_id:
            return Response({'error': 'service_subcategory is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        subcategory = ServiceSubCategory.objects.get(id=subcategory_id)
        
        # Collect form data
        form_data = {}
        for key, value in request.data.items():
            if key not in ['service_subcategory', 'customer_name', 'customer_email', 
                          'customer_phone', 'amount', 'notes', 'status']:
                form_data[key] = value
        
        # Create a minimal service form for this submission
        service_form = ServiceForm.objects.create(
            service_type='direct_submission',
            service_subcategory=subcategory,
            name=f"Direct Form - {subcategory.name}",
            description=f"Auto-generated form for {subcategory.name}",
            created_by=request.user if request.user.is_authenticated else None
        )
        
        # Create submission - DON'T include submitted_by in the data
        submission_data = {
            'service_form': service_form.id,
            'service_subcategory': subcategory.id,
            'form_data': form_data,
            'status': 'submitted',
            'amount': request.data.get('amount', 0),
            'customer_name': request.data.get('customer_name', ''),
            'customer_email': request.data.get('customer_email', ''),
            'customer_phone': request.data.get('customer_phone', ''),
            'notes': request.data.get('notes', ''),
            # Remove submitted_by completely from here
        }
        
        serializer = ServiceSubmissionSerializer(data=submission_data)
        if serializer.is_valid():
            # Pass submitted_by separately during save
            submission = serializer.save(submitted_by=request.user if request.user.is_authenticated else None)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            service_form.delete()
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
    except ServiceSubCategory.DoesNotExist:
        return Response({'error': 'Subcategory not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
