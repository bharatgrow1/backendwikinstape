from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from . import services
from rest_framework.viewsets import ViewSet
from rest_framework.decorators import action, api_view
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from users.models import Wallet 
from .models import CreditLinkTransaction
from .serializers import CreditLinkResponseSerializer, CreditApplySerializer
from .services.manager import credit_manager


class CreditLinkViewSet(ViewSet):

    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['post'])
    def apply(self, request):

        serializer = CreditApplySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        result = credit_manager.generate_link(request.user)

        txn = CreditLinkTransaction.objects.create(
            user=request.user,
            customer_name=serializer.validated_data["name"],
            customer_mobile=serializer.validated_data["mobile"],
            customer_pan=serializer.validated_data.get("pan"),
            customer_city=serializer.validated_data.get("city"),
            redirect_url=result.get("redirect_url"),
            status='pending' if result["success"] else 'failed',
            api_response=result.get("raw")
        )

        return Response({
            "success": result["success"],
            "redirect_url": result.get("redirect_url"),
            "transaction_id": txn.transaction_id
        })

    @action(detail=False, methods=['get'])
    def history(self, request):

        transactions = CreditLinkTransaction.objects.filter(user=request.user)
        serializer = CreditLinkResponseSerializer(transactions, many=True)

        return Response({
            "success": True,
            "transactions": serializer.data
        })




@api_view(["POST"])
def credit_webhook(request):

    data = request.data

    transaction_id = data.get("transaction_id")
    status = data.get("status")
    commission = data.get("commission_amount", 0)
    bank_ref = data.get("bank_reference_id")

    try:
        txn = CreditLinkTransaction.objects.get(transaction_id=transaction_id)

        txn.status = status.lower()
        txn.commission_amount = commission
        txn.bank_reference_id = bank_ref
        txn.save()

        if status.lower() == "approved" and commission:

            wallet = Wallet.objects.get(user=txn.user)
            wallet.balance += float(commission)
            wallet.save()

        return Response({"success": True})

    except CreditLinkTransaction.DoesNotExist:
        return Response({"error": "Transaction not found"}, status=404)
    




class CreditLinksViewSet(viewsets.ViewSet):

    @action(detail=False, methods=["post"])
    def dedupe(self, request):
        result = services.dedupe_api(request.data["mobile"])
        return Response(result["data"], status=result["status_code"])


    @action(detail=False, methods=["post"])
    def personal_create(self, request):
        result = services.create_personal_loan(request.data)
        return Response(result["data"], status=result["status_code"])


    @action(detail=False, methods=["post"])
    def personal_update(self, request):
        result = services.update_lead(
            request.data["lead_id"],
            request.data
        )
        return Response(result["data"], status=result["status_code"])


    @action(detail=False, methods=["post"])
    def personal_offers(self, request):
        result = services.get_offers(request.data["lead_id"])
        return Response(result["data"], status=result["status_code"])


    @action(detail=False, methods=["post"])
    def personal_summary(self, request):
        result = services.get_summary(request.data["lead_id"])
        return Response(result["data"], status=result["status_code"])


    @action(detail=False, methods=["post"])
    def gold_create(self, request):
        result = services.create_gold_loan(request.data)
        return Response(result["data"], status=result["status_code"])


    @action(detail=False, methods=["post"])
    def gold_status(self, request):
        result = services.gold_status(request.data["lead_id"])
        return Response(result["data"], status=result["status_code"])


    @action(detail=False, methods=["post"])
    def housing_create(self, request):
        result = services.create_housing_loan(request.data)
        return Response(result["data"], status=result["status_code"])
