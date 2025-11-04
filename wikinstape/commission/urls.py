from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()

router.register(r'commission-plans', views.CommissionPlanViewSet, basename='commission-plans')
router.register(r'service-commissions', views.ServiceCommissionViewSet, basename='service-commissions')
router.register(r'commission-transactions', views.CommissionTransactionViewSet, basename='commission-transactions')
router.register(r'user-commission-plans', views.UserCommissionPlanViewSet, basename='user-commission-plans')
router.register(r'commission-payouts', views.CommissionPayoutViewSet, basename='commission-payouts')
router.register(r'commission-calculator', views.CommissionCalculatorView, basename='commission-calculator')
router.register(r'commission-stats', views.CommissionStatsViewSet, basename='commission-stats')

urlpatterns = [
    path('', include(router.urls)),
]