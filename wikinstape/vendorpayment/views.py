from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from .serializers import VendorPaymentSerializer
from .services.vendor_manager import vendor_manager


class VendorPaymentViewSet(viewsets.ViewSet):

    @action(detail=False, methods=["post"])
    def pay(self, request):
        serializer = VendorPaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(vendor_manager.initiate_payment(serializer.validated_data))
