from django.urls import path, include
from rest_framework.routers import DefaultRouter
from dmt.views import (DMTViewSet, DMTKYCViewSet, DMTRecipientViewSet, 
                   DMTTransactionViewSet, DMTLimitViewSet, DMTAdminViewSet)

router = DefaultRouter()
router.register(r'dashboard', DMTViewSet, basename='dmt-dashboard')
router.register(r'kyc', DMTKYCViewSet, basename='dmt-kyc')
router.register(r'recipients', DMTRecipientViewSet, basename='dmt-recipients')
router.register(r'transactions', DMTTransactionViewSet, basename='dmt-transactions')
router.register(r'limits', DMTLimitViewSet, basename='dmt-limits')
router.register(r'admin', DMTAdminViewSet, basename='dmt-admin')

urlpatterns = [
    path('', include(router.urls)),
]