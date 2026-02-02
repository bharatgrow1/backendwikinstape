from uuid import uuid4
from decimal import Decimal
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response

from .models import CMSTransaction, CMSBiller
from .serializers import GenerateCMSUrlSerializer
from .services.eko_cms_service import EkoCMSService


class CMSViewSet(viewsets.ViewSet):
    """
    CMS APIs:
    - generate CMS url
    - debit hook
    - callback
    - biller list
    """

    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=["post"])
    def generate_url(self, request):
        serializer = GenerateCMSUrlSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        biller = CMSBiller.objects.get(
            biller_id=serializer.validated_data["biller_id"],
            is_active=True
        )

        client_ref_id = f"CMS{uuid4().hex[:10].upper()}"

        txn = CMSTransaction.objects.create(
            user=request.user,
            client_ref_id=client_ref_id,
            biller=biller
        )

        service = EkoCMSService()
        response = service.generate_cms_url({
            "client_ref_id": client_ref_id,
            "initiator_id": service.initiator_id,
            "latlong": serializer.validated_data["latlong"],
            "locale": "en"
        })

        if response.get("response_status_id") == 0:
            txn.tid = response["data"]["tid"]
            txn.status = "redirected"
            txn.save()

            return Response({
                "success": True,
                "redirect_url": response["data"]["redirectionUrl"],
                "biller": biller.company_name
            })

        return Response(response, status=400)

    @action(detail=False, methods=["post"], permission_classes=[AllowAny])
    def debit_hook(self, request):
        tid = request.data.get("tid")
        amount = Decimal(request.data.get("amount", 0))

        txn = CMSTransaction.objects.filter(tid=tid).select_related("user").first()
        if not txn:
            return Response({"proceed": 0})

        if txn.status in ["processing", "success"]:
            return Response({"ekoTxnId": tid, "proceed": 1})

        wallet = txn.user.wallet

        if wallet.balance >= amount:
            wallet.balance -= amount
            wallet.save()

            txn.amount = amount
            txn.status = "processing"
            txn.debit_hook_payload = request.data
            txn.save()

            return Response({"ekoTxnId": tid, "proceed": 1})

        return Response({"ekoTxnId": tid, "proceed": 0})

    @action(detail=False, methods=["post"], permission_classes=[AllowAny])
    def callback(self, request):
        tid = request.data.get("tid")

        txn = CMSTransaction.objects.filter(tid=tid).first()
        if not txn:
            return Response({"status": "ignored"})

        if txn.status == "success":
            return Response({"status": "already_processed"})

        txn.callback_payload = request.data

        if request.data.get("tx_status") == 0:
            txn.status = "success"
            txn.commission = request.data.get("partners_commision", 0)
        else:
            txn.status = "failed"

        txn.save()
        return Response({"status": "ok"})

    @action(detail=False, methods=["get"])
    def billers(self, request):
        billers = CMSBiller.objects.filter(is_active=True)
        return Response([
            {
                "biller_id": b.biller_id,
                "company_name": b.company_name,
                "type": b.biller_type
            }
            for b in billers
        ])
