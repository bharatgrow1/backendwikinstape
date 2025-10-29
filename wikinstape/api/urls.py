from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import SignUPRequestViewSet

router = DefaultRouter()
router.register(r'', SignUPRequestViewSet)

urlpatterns = [
    path('', include(router.urls)),
]