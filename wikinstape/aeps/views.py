from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated

from .serializers import OnboardMerchantSerializer
from .services.manager import AEPSManager

class AEPSMerchantViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=["post"])
    def onboard(self, request):
        serializer = OnboardMerchantSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        manager = AEPSManager()
        result = manager.onboard_merchant(serializer.validated_data)

        return Response(result, status=200 if result["success"] else 400)
