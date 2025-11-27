from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (DMTOnboardViewSet, DMTProfileViewSet, DMTKYCViewSet, 
                   DMTRecipientViewSet, DMTTransactionViewSet)

router = DefaultRouter()
router.register(r'onboard', DMTOnboardViewSet, basename='dmt-onboard')
router.register(r'profile', DMTProfileViewSet, basename='dmt-profile')
router.register(r'kyc', DMTKYCViewSet, basename='dmt-kyc')
router.register(r'recipient', DMTRecipientViewSet, basename='dmt-recipient')
router.register(r'transaction', DMTTransactionViewSet, basename='dmt-transaction')

urlpatterns = [
    path('', include(router.urls)),
]