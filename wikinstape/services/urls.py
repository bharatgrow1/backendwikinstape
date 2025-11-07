from django.urls import path, include
from rest_framework.routers import DefaultRouter
from services.views import (ServiceCategoryViewSet, ServiceSubCategoryViewSet, ServiceFormViewSet, DirectServiceFormViewSet,
    ServiceSubmissionViewSet, ServiceImageViewSet, get_subcategory_form_config, get_category_form_config, 
    create_form_from_boolean_fields, create_direct_category_form, copy_category_fields_to_subcategory,
    get_categories_with_direct_services, create_service_submission_direct)

router = DefaultRouter()
router.register(r'categories', ServiceCategoryViewSet)
router.register(r'subcategories', ServiceSubCategoryViewSet)
router.register(r'service-forms', ServiceFormViewSet)
router.register(r'direct-service-forms', DirectServiceFormViewSet, basename='direct-service-form')
router.register(r'service-submissions', ServiceSubmissionViewSet)
router.register(r'upload-images', ServiceImageViewSet)


urlpatterns = [
    path('', include(router.urls)),
    path('subcategory-form-config/<int:subcategory_id>/', get_subcategory_form_config, name='subcategory-form-config'),
    path('category-form-config/<int:category_id>/', get_category_form_config, name='category-form-config'),
    path('create-form-from-boolean/', create_form_from_boolean_fields, name='create-form-from-boolean'),
    path('create-direct-category-form/', create_direct_category_form, name='create-direct-category-form'),
    path('copy-category-fields/', copy_category_fields_to_subcategory, name='copy-category-fields'),
    path('categories-with-direct-services/', get_categories_with_direct_services, name='categories-with-direct-services'),
    path('create-submission-direct/', create_service_submission_direct, name='create-submission-direct'),
]