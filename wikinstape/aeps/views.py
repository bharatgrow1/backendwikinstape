from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from aeps.serializers import AEPSActivationSerializer, OTPRequestSerializer

from .serializers import OnboardMerchantSerializer
from .services.aeps_manager import AEPSManager

class AEPSMerchantViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=["post"])
    def onboard(self, request):
        serializer = OnboardMerchantSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        manager = AEPSManager()
        result = manager.onboard_merchant(serializer.validated_data)

        return Response(result, status=200 if result["success"] else 400)
    

    @action(detail=False, methods=["get"])
    def services(self, request):
        manager = AEPSManager()
        response = manager.get_available_services()
        return Response(response)
    


    @action(detail=False, methods=["post"])
    def activate(self, request):
        serializer = AEPSActivationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        manager = AEPSManager()
        result = manager.activate_aeps(serializer.validated_data)

        return Response(result)
    

    @action(detail=False, methods=["post"])
    def request_otp(self, request):
        serializer = OTPRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        mobile = serializer.validated_data["mobile"]

        manager = AEPSManager()
        result = manager.request_otp(mobile)

        return Response(result)



