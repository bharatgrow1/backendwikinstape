from rest_framework.routers import DefaultRouter
from .views import CreditLinkViewSet
from django.urls import path


router = DefaultRouter()
router.register(r'', CreditLinkViewSet, basename='creditlinks')

urlpatterns = router.urls


from .views import credit_webhook

urlpatterns += [
    path("webhook/", credit_webhook)
]



# https://yourdomain.com/apis/creditlinks/webhook/