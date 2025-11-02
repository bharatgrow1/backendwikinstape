from api.views import *
from users.views import *
from services.views import *
from rest_framework import routers
from rest_framework.routers import DefaultRouter

router = DefaultRouter()

#api
router.register(r'singup-request', SignUPRequestViewSet)

# Users
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


#services
router.register(r'categories', ServiceCategoryViewSet)
router.register(r'subcategories', ServiceSubCategoryViewSet)
router.register(r'service-forms', ServiceFormViewSet)
router.register(r'direct-service-forms', DirectServiceFormViewSet, basename='direct-service-form')
router.register(r'service-submissions', ServiceSubmissionViewSet)
router.register(r'upload-images', ServiceImageViewSet)


