from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ServiceCategoryViewSet, ServiceSubCategoryViewSet, ServiceFormViewSet, 
    ServiceSubmissionViewSet, ServiceImageViewSet,
    get_subcategory_form_config, create_form_from_boolean_fields, create_service_submission_direct
)

router = DefaultRouter()
router.register(r'categories', ServiceCategoryViewSet)
router.register(r'subcategories', ServiceSubCategoryViewSet)
router.register(r'service-forms', ServiceFormViewSet)
router.register(r'service-submissions', ServiceSubmissionViewSet)
router.register(r'upload-images', ServiceImageViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('subcategory-form-config/<int:subcategory_id>/', get_subcategory_form_config, name='subcategory-form-config'),
    path('create-form-from-boolean/', create_form_from_boolean_fields, name='create-form-from-boolean'),
    path('create-submission-direct/', create_service_submission_direct, name='create-submission-direct'),
]
