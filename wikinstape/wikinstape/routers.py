from rest_framework.routers import DefaultRouter
from rest_framework import routers
from api.views import *
from users.views import *
from services.views import *
from commission.views import *

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


# Existing routes...
router.register(r'commission-plans', CommissionPlanViewSet, basename='commission-plans')
router.register(r'service-commissions', ServiceCommissionViewSet, basename='service-commissions')
router.register(r'commission-transactions', CommissionTransactionViewSet, basename='commission-transactions')
router.register(r'user-commission-plans', UserCommissionPlanViewSet, basename='user-commission-plans')
router.register(r'commission-payouts', CommissionPayoutViewSet, basename='commission-payouts')
router.register(r'my-service-commissions', DealerRetailerCommissionViewSet, basename='my-service-commissions')

router.register(r'user-hierarchy', UserHierarchyViewSet, basename='user-hierarchy')
router.register(r'commission-dashboard', CommissionDashboardViewSet, basename='commission-dashboard')