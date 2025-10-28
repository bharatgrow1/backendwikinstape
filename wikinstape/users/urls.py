from rest_framework.routers import DefaultRouter
from .views import (
    AuthViewSet, UserViewSet, WalletViewSet, TransactionViewSet, 
    BalanceRequestViewSet, PermissionViewSet
)
from services.views import ServiceImageViewSet

router = DefaultRouter()
router.register(r'images', ServiceImageViewSet)
router.register(r'auth', AuthViewSet, basename='auth')
router.register(r'users', UserViewSet, basename='users')
router.register(r'wallets', WalletViewSet, basename='wallets')
router.register(r'transactions', TransactionViewSet, basename='transactions')
router.register(r'balance-requests', BalanceRequestViewSet, basename='balance-requests')
router.register(r'permissions', PermissionViewSet, basename='permissions')

urlpatterns = router.urls