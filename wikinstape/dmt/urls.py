from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import DMTViewSet, DMTRecipientViewSet

router = DefaultRouter()
router.register(r'dmt', DMTViewSet, basename='dmt')
router.register(r'recipients', DMTRecipientViewSet, basename='dmt-recipients')

urlpatterns = [
    path('', include(router.urls)),
]