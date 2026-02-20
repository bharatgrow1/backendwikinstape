from rest_framework import viewsets
from rest_framework.decorators import action, api_view
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from decimal import Decimal
from django.conf import settings
from django.db import transaction

from . import creditlinks_api as services
from .models import CreditLinkTransaction, Loan
from .serializers import CreditLinkResponseSerializer, CreditApplySerializer
from .services.manager import credit_manager
from users.models import Wallet


class CreditLinkViewSet(viewsets.ViewSet):

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
        return Response({"success": True, "transactions": serializer.data})



@api_view(["POST"])
def credit_webhook(request):

    secret = request.headers.get("X-WEBHOOK-SECRET")
    if secret != settings.CREDIT_WEBHOOK_SECRET:
        return Response({"error": "Unauthorized"}, status=403)

    data = request.data
    lead_id = data.get("lead_id")
    status_value = data.get("status")
    commission = data.get("commission_amount", 0)

    try:
        with transaction.atomic():

            loan = Loan.objects.select_for_update().get(lead_id=lead_id)

            if loan.status == "approved" and loan.commission:
                return Response({"success": True, "message": "Already processed"})

            loan.status = status_value.lower()
            loan.commission = Decimal(str(commission or 0))
            loan.external_response = data
            loan.save()

            if status_value.lower() == "approved" and commission:
                wallet = Wallet.objects.select_for_update().get(user=loan.user)
                wallet.balance += Decimal(str(commission))
                wallet.save(update_fields=["balance"])

        return Response({"success": True})

    except Loan.DoesNotExist:
        return Response({"error": "Loan not found"}, status=404)


class CreditLinksViewSet(viewsets.ViewSet):

    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=["post"])
    def dedupe(self, request):
        result = services.dedupe_api(request.data.get("mobile"))
        return Response(result["data"], status=result["status_code"])


    @action(detail=False, methods=["post"])
    def personal_create(self, request):

        result = services.create_personal_loan(request.data)

        if result["status_code"] == 200 and result["data"].get("leadId"):

            Loan.objects.get_or_create(
                lead_id=result["data"].get("leadId"),
                defaults={
                    "user": request.user,
                    "loan_type": "personal",
                    "mobile": request.data.get("mobile"),
                    "first_name": request.data.get("first_name"),
                    "last_name": request.data.get("last_name"),
                    "status": "created",
                    "external_response": result["data"]
                }
            )

        return Response(result["data"], status=result["status_code"])


    @action(detail=False, methods=["post"])
    def personal_offers(self, request):
        result = services.get_offers(request.data.get("lead_id"))
        return Response(result["data"], status=result["status_code"])


    @action(detail=False, methods=["post"])
    def gold_create(self, request):

        result = services.create_gold_loan(request.data)

        if result["status_code"] == 200 and result["data"].get("leadId"):

            Loan.objects.get_or_create(
                lead_id=result["data"].get("leadId"),
                defaults={
                    "user": request.user,
                    "loan_type": "gold",
                    "mobile": request.data.get("mobile"),
                    "first_name": request.data.get("first_name"),
                    "last_name": request.data.get("last_name"),
                    "status": "created",
                    "external_response": result["data"]
                }
            )

        return Response(result["data"], status=result["status_code"])


    @action(detail=False, methods=["post"])
    def gold_status(self, request):
        result = services.gold_status(request.data.get("lead_id"))
        return Response(result["data"], status=result["status_code"])


    @action(detail=False, methods=["post"])
    def housing_create(self, request):

        result = services.create_housing_loan(request.data)

        if result["status_code"] == 200 and result["data"].get("leadId"):

            Loan.objects.get_or_create(
                lead_id=result["data"].get("leadId"),
                defaults={
                    "user": request.user,
                    "loan_type": "housing",
                    "mobile": request.data.get("mobile"),
                    "first_name": request.data.get("first_name"),
                    "last_name": request.data.get("last_name"),
                    "status": "created",
                    "external_response": result["data"]
                }
            )

        return Response(result["data"], status=result["status_code"])


    @action(detail=False, methods=["get"])
    def my_loans(self, request):

        loans = Loan.objects.filter(user=request.user).order_by("-created_at")

        data = []
        for loan in loans:
            data.append({
                "loan_type": loan.loan_type,
                "mobile": loan.mobile,
                "lead_id": loan.lead_id,
                "status": loan.status,
                "commission": loan.commission,
                "created_at": loan.created_at
            })

        return Response(data)