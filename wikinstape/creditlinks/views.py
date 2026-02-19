from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from . import services


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
