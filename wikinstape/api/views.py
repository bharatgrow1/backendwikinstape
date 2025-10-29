from rest_framework import viewsets
from .models import SignUPRequest
from .serializers import SignUPRequestSerializer

class SignUPRequestViewSet(viewsets.ModelViewSet):
    queryset = SignUPRequest.objects.all().order_by('-created_at')
    serializer_class = SignUPRequestSerializer