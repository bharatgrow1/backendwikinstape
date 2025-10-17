from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ServiceCategoryViewSet, ServiceSubCategoryViewSet, ServiceFormViewSet, ServiceSubmissionViewSet

router = DefaultRouter()
router.register(r'categories', ServiceCategoryViewSet)
router.register(r'subcategories', ServiceSubCategoryViewSet)
router.register(r'service-forms', ServiceFormViewSet)
router.register(r'service-submissions', ServiceSubmissionViewSet)

urlpatterns = [
    path('', include(router.urls)),
]