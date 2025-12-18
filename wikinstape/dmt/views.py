from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
import logging
import json
from django.db import transaction as db_transaction
from decimal import Decimal
from users.models import Wallet, Transaction


from .services.dmt_manager import dmt_manager
from .serializers import (
    DMTOnboardSerializer, DMTGetProfileSerializer, DMTBiometricKycSerializer,
    DMTKycOTPVerifySerializer, DMTAddRecipientSerializer, DMTGetRecipientsSerializer,
    DMTSendTxnOTPSerializer, DMTInitiateTransactionSerializer, DMTCreateCustomerSerializer,
    DMTVerifyCustomerSerializer, DMTResendOTPSerializer, EkoBankSerializer, 
    DMTTransactionInquirySerializer, DMTRefundSerializer, DMTRefundOTPResendSerializer
)

from .models import EkoBank, DMTTransaction, DMTServiceCharge

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
    
    # @action(detail=False, methods=['post'])
    # def initiate_transaction(self, request):
    #     """
    #     Initiate Transaction
    #     POST /api/dmt/transaction/initiate_transaction/
    #     """
    #     serializer = DMTInitiateTransactionSerializer(data=request.data)
    #     serializer.is_valid(raise_exception=True)
        
    #     response = dmt_manager.initiate_transaction(
    #         serializer.validated_data['customer_id'],
    #         serializer.validated_data['recipient_id'],
    #         serializer.validated_data['amount'],
    #         serializer.validated_data['otp'],
    #         serializer.validated_data['otp_ref_id']
    #     )
    #     return Response(response)




    @action(detail=False, methods=['post'])
    @db_transaction.atomic
    def initiate_transaction(self, request):

        serializer = DMTInitiateTransactionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user
        pin = serializer.validated_data['pin']

        # 🔐 Wallet verification
        wallet = user.wallet
        if not wallet.verify_pin(pin):
            return Response({
                "status": 1,
                "message": "Invalid wallet PIN"
            })

        amount = Decimal(serializer.validated_data['amount'])

        # 💰 Service charge
        service_charge = DMTServiceCharge.calculate_charge(amount)
        total_deduction = amount + service_charge

        if wallet.balance < total_deduction:
            return Response({
                "status": 1,
                "message": f"Insufficient wallet balance. Required ₹{total_deduction}"
            })

        # 🔻 WALLET DEBIT
        wallet.balance -= total_deduction
        wallet.save()

        Transaction.objects.create(
            user=user,
            amount=total_deduction,
            transaction_type="debit",
            description="DMT Money Transfer"
        )

        # 🧾 Create local DMT record
        dmt_txn = DMTTransaction.objects.create(
            user=user,
            amount=amount,
            service_charge=service_charge,
            total_amount=total_deduction,
            sender_mobile=serializer.validated_data['customer_id'],
            status='processing'
        )

        # 🔗 EKO API CALL
        response = dmt_manager.initiate_transaction(
            serializer.validated_data['customer_id'],
            serializer.validated_data['recipient_id'],
            amount,
            serializer.validated_data['otp'],
            serializer.validated_data['otp_ref_id']
        )

        # ❌ FAILURE → REFUND
        if response.get("status") != 0:
            wallet.balance += total_deduction
            wallet.save()

            Transaction.objects.create(
                user=user,
                amount=total_deduction,
                transaction_type="credit",
                description="DMT Refund"
            )

            dmt_txn.status = "failed"
            dmt_txn.status_message = response.get("message", "EKO Failed")
            dmt_txn.save()

            return Response(response)

        # ✅ SUCCESS
        dmt_txn.status = "success"
        dmt_txn.api_response = response
        dmt_txn.save()

        return Response(response)

    

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