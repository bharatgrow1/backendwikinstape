from rest_framework.routers import DefaultRouter
from .views import *
from services.views import *

router = DefaultRouter()
router.register(r'images', ServiceImageViewSet)
router.register(r'auth', AuthViewSet, basename='auth')
router.register(r'users', UserViewSet, basename='users')
router.register(r'wallets', WalletViewSet, basename='wallets')
router.register(r'transactions', TransactionViewSet, basename='transactions')
router.register(r'permissions', PermissionViewSet, basename='permissions')
router.register(r'onboardservices', OnBoardServiceViewSet, basename='services')
router.register(r'states', StateViewSet, basename='states')
router.register(r'cities', CityViewSet, basename='cities')
router.register(r'fund-requests', FundRequestViewSet, basename='fund-requests')
router.register(r'service-charges', ServiceChargeViewSet, basename='service-charges')
router.register(r'user-hierarchy', UserHierarchyViewSet, basename='user-hierarchy')

urlpatterns = router.urls