from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register('user', views.EkoUserViewSet, basename='eko-user')
router.register('bbps', views.EkoBBPSViewSet, basename='eko-bbps')
router.register('recharge', views.EkoRechargeViewSet, basename='eko-recharge')
router.register('dmt', views.EkoDMTViewSet, basename='eko-dmt')

urlpatterns = [
    path('eko/', include(router.urls)),
]