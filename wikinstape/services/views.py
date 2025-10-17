from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from django.db import transaction

from .models import (ServiceCategory, ServiceSubCategory, ServiceForm, ServiceSubmission)
from .serializers import (ServiceCategorySerializer, ServiceSubCategorySerializer, ServiceFormSerializer,
                           ServiceSubmissionSerializer, DynamicFormSubmissionSerializer, ServiceFormWithFieldsSerializer)

class ServiceCategoryViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = ServiceCategory.objects.all()
    serializer_class = ServiceCategorySerializer

    def get_queryset(self):
        queryset = ServiceCategory.objects.all()
        # Only show active categories to non-admin users
        if not self.request.user.is_admin_user():
            queryset = queryset.filter(is_active=True)
        return queryset

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(created_by=self.request.user)

class ServiceSubCategoryViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = ServiceSubCategory.objects.all()
    serializer_class = ServiceSubCategorySerializer

    def get_queryset(self):
        queryset = ServiceSubCategory.objects.all()
        category_id = self.request.query_params.get('category_id')
        
        # Filter by category if provided
        if category_id:
            queryset = queryset.filter(category_id=category_id)
        
        # Only show active subcategories to non-admin users
        if not self.request.user.is_admin_user():
            queryset = queryset.filter(is_active=True, category__is_active=True)
            
        return queryset

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=False, methods=['get'])
    def by_category(self, request):
        """Get subcategories by category ID"""
        category_id = request.query_params.get('category_id')
        if not category_id:
            return Response(
                {'error': 'category_id parameter is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        subcategories = ServiceSubCategory.objects.filter(category_id=category_id, is_active=True)
        serializer = self.get_serializer(subcategories, many=True)
        return Response(serializer.data)
    


class ServiceFormViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
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
        
        if not self.request.user.is_staff:
            queryset = queryset.filter(is_active=True)
            
        return queryset

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=['get'])
    def form_config(self, request, pk=None):
        """Get complete form configuration with fields"""
        service_form = self.get_object()
        serializer = ServiceFormWithFieldsSerializer(service_form)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def by_service_type(self, request):
        """Get forms by service type"""
        service_type = request.query_params.get('service_type')
        if not service_type:
            return Response(
                {'error': 'service_type parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        forms = self.get_queryset().filter(service_type=service_type, is_active=True)
        serializer = self.get_serializer(forms, many=True)
        return Response(serializer.data)

class ServiceSubmissionViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = ServiceSubmission.objects.all()
    serializer_class = ServiceSubmissionSerializer
    parser_classes = [MultiPartParser, FormParser]

    def get_queryset(self):
        queryset = ServiceSubmission.objects.all()
        
        # Non-admin users can only see their own submissions
        if not self.request.user.is_staff:
            queryset = queryset.filter(submitted_by=self.request.user)
        
        # Filter by form or service type
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
        service_form = get_object_or_404(ServiceForm, id=form_id, is_active=True)
        
        # Get form fields for validation
        form_fields = service_form.fields.filter(is_active=True).order_by('order')
        
        # Extract form data
        form_data = {}
        files_to_save = {}
        
        for field in form_fields:
            field_name = field.field_name
            if field_name in request.data:
                form_data[field_name] = request.data[field_name]
            elif field_name in request.FILES:
                files_to_save[field_name] = request.FILES[field_name]
        
        # Validate form data
        dynamic_serializer = DynamicFormSubmissionSerializer(
            data=form_data,
            form_fields=form_fields
        )
        
        if not dynamic_serializer.is_valid():
            return Response(
                {'errors': dynamic_serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create submission
        submission_data = {
            'service_form': service_form.id,
            'service_subcategory': service_form.service_subcategory.id,
            'submitted_by': request.user.id,
            'customer_name': request.data.get('customer_name'),
            'customer_email': request.data.get('customer_email'),
            'customer_phone': request.data.get('customer_phone'),
            'form_data': dynamic_serializer.validated_data,
            'status': 'submitted',
            'amount': request.data.get('amount', 0),
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
        """Update submission status"""
        submission = self.get_object()
        new_status = request.data.get('status')
        
        if new_status not in dict(ServiceSubmission.STATUS_CHOICES):
            return Response(
                {'error': 'Invalid status'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        submission.status = new_status
        submission.save()
        
        serializer = self.get_serializer(submission)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def my_submissions(self, request):
        """Get current user's submissions"""
        submissions = self.get_queryset().filter(submitted_by=request.user)
        serializer = self.get_serializer(submissions, many=True)
        return Response(serializer.data)