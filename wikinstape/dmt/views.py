from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
import logging
import json

from .services.dmt_manager import dmt_manager
from .serializers import (
    DMTOnboardSerializer, DMTGetProfileSerializer, DMTBiometricKycSerializer,
    DMTKycOTPVerifySerializer, DMTAddRecipientSerializer, DMTGetRecipientsSerializer,
    DMTSendTxnOTPSerializer, DMTInitiateTransactionSerializer, DMTCreateCustomerSerializer,
    DMTVerifyCustomerSerializer, DMTResendOTPSerializer, EkoBankSerializer, 
    DMTTransactionInquirySerializer, DMTRefundSerializer, DMTRefundOTPResendSerializer, DMTTransactionSerializer
)

from .models import EkoBank, DMTTransaction

logger = logging.getLogger(__name__)

class DMTOnboardViewSet(viewsets.ViewSet):
    permission_classes = [AllowAny]
    
    @action(detail=False, methods=['post'])
    def onboard_user(self, request):
        """
        User Onboarding
        POST /api/dmt/onboard/onboard_user/
        """
        serializer = DMTOnboardSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        response = dmt_manager.onboard_user(serializer.validated_data)
        return Response(response)
    


class DMTCustomerVerificationViewSet(viewsets.ViewSet):
    permission_classes = [AllowAny]
    
    @action(detail=False, methods=['post'])
    def verify_customer(self, request):
        """
        Verify Customer with OTP
        POST /api/dmt/verification/verify_customer/
        """
        try:
            serializer = DMTVerifyCustomerSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            response = dmt_manager.verify_customer_identity(
                serializer.validated_data['customer_mobile'],
                serializer.validated_data['otp'],
                serializer.validated_data['otp_ref_id']
            )
            
            return Response(response)
            
        except Exception as e:
            logger.error(f"Verify customer error: {str(e)}")
            return Response({
                "status": 1,
                "message": f"Failed to verify customer: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['post'])
    def resend_otp(self, request):
        """
        Resend OTP for verification
        POST /api/dmt/verification/resend_otp/
        """
        try:
            serializer = DMTResendOTPSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            response = dmt_manager.resend_otp(
                serializer.validated_data['customer_mobile']
            )
            
            return Response(response)
            
        except Exception as e:
            logger.error(f"Resend OTP error: {str(e)}")
            return Response({
                "status": 1,
                "message": f"Failed to resend OTP: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    


class DMTCustomerViewSet(viewsets.ViewSet):
    permission_classes = [AllowAny]
    
    @action(detail=False, methods=['post'])
    def create_customer(self, request):
        """
        Create Customer for DMT
        POST /api/dmt/customer/create_customer/
        
        Call this when Get Sender Profile returns "Customer Not Enrolled"
        """
        try:
            serializer = DMTCreateCustomerSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            response = dmt_manager.create_customer(serializer.validated_data)
            
            return Response(response)
            
        except Exception as e:
            logger.error(f"Create customer error: {str(e)}")
            return Response({
                "status": 1,
                "message": f"Failed to create customer: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        

class DMTProfileViewSet(viewsets.ViewSet):
    permission_classes = [AllowAny]
    
    @action(detail=False, methods=['post'])
    def get_sender_profile(self, request):
        """
        Get Sender Profile
        POST /api/dmt/profile/get_sender_profile/
        """
        serializer = DMTGetProfileSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        response = dmt_manager.get_sender_profile(
            serializer.validated_data['customer_mobile']
        )
        return Response(response)

class DMTKYCViewSet(viewsets.ViewSet):
    permission_classes = [AllowAny]
    
    @action(detail=True, methods=['post'], url_path='biometric_kyc')
    def biometric_kyc(self, request, pk=None):
        """
        POST /api/dmt/kyc/<customer_id>/biometric_kyc/
        """
        aadhar = request.data.get("aadhar")
        piddata = request.data.get("piddata")

        if not aadhar or not piddata:
            return Response({
                "status": 0,
                "message": "Missing Data"
            }, status=status.HTTP_400_BAD_REQUEST)

        response = dmt_manager.customer_ekyc_biometric(
            pk,
            aadhar,
            piddata
        )

        return Response(response)
    
    @action(detail=False, methods=['post'])
    def verify_kyc_otp(self, request):
        """
        Verify KYC OTP
        POST /api/dmt/kyc/verify_kyc_otp/
        """
        serializer = DMTKycOTPVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        response = dmt_manager.verify_ekyc_otp(
            serializer.validated_data['customer_id'],
            serializer.validated_data['otp'],
            serializer.validated_data['otp_ref_id'],
            serializer.validated_data['kyc_request_id']
        )
        return Response(response)

class DMTRecipientViewSet(viewsets.ViewSet):
    permission_classes = [AllowAny]
    
    @action(detail=False, methods=['post'])
    def add_recipient(self, request):
        """
        Add Recipient
        POST /api/dmt/recipient/add_recipient/
        """
        serializer = DMTAddRecipientSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        response = dmt_manager.add_recipient(
            serializer.validated_data['customer_id'],
            serializer.validated_data
        )
        return Response(response)
    
    @action(detail=False, methods=['post'])
    def get_recipient_list(self, request):
        """
        Get Recipient List
        POST /api/dmt/recipient/get_recipient_list/
        """
        serializer = DMTGetRecipientsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        response = dmt_manager.get_recipient_list(
            serializer.validated_data['customer_id']
        )
        return Response(response)

class DMTTransactionViewSet(viewsets.ViewSet):
    permission_classes = [AllowAny]
    
    @action(detail=False, methods=['post'])
    def send_transaction_otp(self, request):
        """
        Send Transaction OTP
        POST /api/dmt/transaction/send_transaction_otp/
        """
        serializer = DMTSendTxnOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        response = dmt_manager.send_transaction_otp(
            serializer.validated_data['customer_id'],
            serializer.validated_data['recipient_id'],
            serializer.validated_data['amount']
        )
        return Response(response)
    
    @action(detail=False, methods=['post'])
    def initiate_transaction(self, request):
        """
        Initiate Transaction with wallet payment
        """
        serializer = DMTInitiateTransactionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        data = serializer.validated_data
        user = request.user
        
        # Add PIN to data
        pin = request.data.get('pin')
        if not pin:
            return Response({
                "status": 1,
                "message": "Wallet PIN is required"
            })
        
        data['pin'] = pin
        data['user'] = user
        
        # Call DMTManager with wallet integration
        from .services.dmt_manager import dmt_manager
        response = dmt_manager.initiate_transaction(
            customer_id=data['customer_id'],
            recipient_id=data['recipient_id'],
            amount=data['amount'],
            otp=data['otp'],
            otp_ref_id=data['otp_ref_id'],
            user=user,
            pin=pin
        )
        
        return Response(response)
    


    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def my_transactions(self, request):
        """Get user's DMT transactions"""
        transactions = DMTTransaction.objects.filter(
            user=request.user
        ).select_related('wallet_transaction').order_by('-initiated_at')
        
        serializer = DMTTransactionSerializer(transactions, many=True)
        return Response({
            'success': True,
            'count': transactions.count(),
            'transactions': serializer.data
        })
    

class BankViewSet(viewsets.ModelViewSet):
    queryset = EkoBank.objects.all().order_by("bank_name")
    serializer_class = EkoBankSerializer
    lookup_field = "bank_id"

    filter_backends = [filters.SearchFilter]
    search_fields = ['bank_name', 'bank_code']



class DMTTransactionInquiryViewSet(viewsets.ViewSet):
    permission_classes = [AllowAny]
    
    @action(detail=False, methods=['post'])
    def check_status(self, request):

        try:
            serializer = DMTTransactionInquirySerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            response = dmt_manager.transaction_inquiry(
                serializer.validated_data['inquiry_id'],
                serializer.validated_data.get('is_client_ref_id', False)
            )
            
            return Response(response)
            
        except Exception as e:
            logger.error(f"Transaction inquiry error: {str(e)}")
            return Response({
                "status": 1,
                "message": f"Failed to check transaction status: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



class DMTRefundViewSet(viewsets.ViewSet):
    permission_classes = [AllowAny]

    @action(detail=False, methods=['post'])
    def refund(self, request):
        """Refund Payment"""
        serializer = DMTRefundSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        tid = serializer.validated_data['tid']
        otp = serializer.validated_data['otp']
        
        response = dmt_manager.refund_transaction(tid, otp)
        return Response(response)

    @action(detail=False, methods=['post'])
    def resend_otp(self, request):
        """
        Resend Refund OTP
        POST /api/dmt/refund/resend_otp/
        """
        serializer = DMTRefundOTPResendSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        tid = serializer.validated_data['tid']

        response = dmt_manager.resend_refund_otp(tid)

        return Response(response)  