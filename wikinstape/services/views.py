from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework.permissions import AllowAny

from .models import (
    ServiceCategory, ServiceSubCategory, ServiceForm, ServiceSubmission, FormSubmissionFile, UploadImage
)
from .serializers import (
    ServiceCategorySerializer, ServiceSubCategorySerializer, ServiceFormSerializer,
    ServiceSubmissionSerializer, DynamicFormSubmissionSerializer, ServiceFormWithFieldsSerializer, UploadImageSerializer
)


# -------------------------------
# Service Category ViewSet
# -------------------------------
class ServiceCategoryViewSet(viewsets.ModelViewSet):
    permission_classes = [AllowAny]  # Fully public
    queryset = ServiceCategory.objects.all()
    serializer_class = ServiceCategorySerializer

    def get_queryset(self):
        return ServiceCategory.objects.all()

    def perform_create(self, serializer):
        serializer.save()


# -------------------------------
# Service SubCategory ViewSet
# -------------------------------
class ServiceSubCategoryViewSet(viewsets.ModelViewSet):
    permission_classes = [AllowAny]
    queryset = ServiceSubCategory.objects.all()
    serializer_class = ServiceSubCategorySerializer

    def get_queryset(self):
        queryset = ServiceSubCategory.objects.all()
        category_id = self.request.query_params.get('category_id')
        if category_id:
            queryset = queryset.filter(category_id=category_id)
        return queryset

    def perform_create(self, serializer):
        serializer.save()

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
        serializer.save()

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

