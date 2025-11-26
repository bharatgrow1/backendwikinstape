from django.urls import path, include
from rest_framework.routers import DefaultRouter
from eko_integration.views import EkoUserViewSet, EkoBBPSViewSet, EkoRechargeViewSet, EkoMoneyTransferViewSet

router = DefaultRouter()
router.register(r'users', EkoUserViewSet, basename='eko-users')
router.register(r'bbps', EkoBBPSViewSet, basename='eko-bbps')
router.register(r'recharge', EkoRechargeViewSet, basename='eko-recharge')
router.register(r'money-transfer', EkoMoneyTransferViewSet, basename='eko-money-transfer')

urlpatterns = [
    path('', include(router.urls)),
]