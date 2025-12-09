# aeps/views.py
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404

from .models import AEPSMerchant, AEPSTransaction
from .serializers import (
    AEPSMerchantSerializer,
    OnboardMerchantSerializer,
    CashWithdrawalSerializer,
    BalanceEnquirySerializer,
    TransactionStatusSerializer,
    AEPSTransactionSerializer
)
from .services.aeps_manager import AEPSManager


class AEPSMerchantViewSet(viewsets.ModelViewSet):
    """ViewSet for managing AEPS merchants"""
    queryset = AEPSMerchant.objects.all()
    serializer_class = AEPSMerchantSerializer
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['post'])
    def onboard(self, request):
        """Onboard a new merchant"""
        serializer = OnboardMerchantSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        aeps_manager = AEPSManager()
        result = aeps_manager.onboard_merchant(serializer.validated_data)
        
        if result['success']:
            return Response(result, status=status.HTTP_201_CREATED)
        else:
            return Response(result, status=status.HTTP_400_BAD_REQUEST)


class AEPSTransactionViewSet(viewsets.ViewSet):
    """ViewSet for AEPS transactions"""
    permission_classes = [IsAuthenticated]
    
    def list(self, request):
        """List all transactions"""
        transactions = AEPSTransaction.objects.all()
        serializer = AEPSTransactionSerializer(transactions, many=True)
        return Response(serializer.data)
    
    def retrieve(self, request, pk=None):
        """Get transaction details"""
        transaction = get_object_or_404(AEPSTransaction, pk=pk)
        serializer = AEPSTransactionSerializer(transaction)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def cash_withdrawal(self, request):
        """Initiate cash withdrawal"""
        serializer = CashWithdrawalSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user_code = request.data.get('user_code') or request.GET.get('user_code')
        if not user_code:
            return Response(
                {'error': 'User code is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        aeps_manager = AEPSManager(user_code=user_code)
        result = aeps_manager.initiate_cash_withdrawal(serializer.validated_data)
        
        return Response(result)
    
    @action(detail=False, methods=['post'])
    def balance_enquiry(self, request):
        """Initiate balance enquiry"""
        serializer = BalanceEnquirySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user_code = request.data.get('user_code') or request.GET.get('user_code')
        if not user_code:
            return Response(
                {'error': 'User code is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        aeps_manager = AEPSManager(user_code=user_code)
        result = aeps_manager.initiate_balance_enquiry(serializer.validated_data)
        
        return Response(result)
    
    @action(detail=False, methods=['post'])
    def mini_statement(self, request):
        """Initiate mini statement (similar to balance enquiry)"""
        # Implementation similar to balance_enquiry
        pass
    
    @action(detail=False, methods=['post'])
    def check_status(self, request):
        """Check transaction status"""
        serializer = TransactionStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user_code = request.data.get('user_code') or request.GET.get('user_code')
        if not user_code:
            return Response(
                {'error': 'User code is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        aeps_manager = AEPSManager(user_code=user_code)
        result = aeps_manager.check_transaction_status(
            serializer.validated_data['client_ref_id']
        )
        
        return Response(result)
    
    @action(detail=False, methods=['get'])
    def get_by_merchant(self, request):
        """Get transactions by merchant"""
        user_code = request.GET.get('user_code')
        if not user_code:
            return Response(
                {'error': 'User code is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            merchant = AEPSMerchant.objects.get(user_code=user_code)
            transactions = AEPSTransaction.objects.filter(merchant=merchant)
            serializer = AEPSTransactionSerializer(transactions, many=True)
            return Response(serializer.data)
        except AEPSMerchant.DoesNotExist:
            return Response(
                {'error': 'Merchant not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )