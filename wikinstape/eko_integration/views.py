from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import transaction
from django.shortcuts import get_object_or_404
import decimal
import json
from .models import EkoUser, EkoService, EkoTransaction, EkoRecipient
from .serializers import *
from .service_handlers import EkoBBPSService, EkoRechargeService, EkoDMTService
from .eko_service import EkoAPIService
from users.models import User, Transaction
import time
import uuid
import logging

logger = logging.getLogger(__name__)

class EkoUserViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['post'])
    def onboard(self, request):
        """Onboard user to Eko platform - Production"""
        serializer = EkoOnboardSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = request.user
        
        # Check if already onboarded
        if hasattr(user, 'eko_user') and user.eko_user.is_verified:
            return Response({
                'status': 'success',
                'message': 'User already onboarded with Eko',
                'eko_user_code': user.eko_user.eko_user_code
            })
        
        # For production, create mock Eko user (replace with actual API call)
        mock_eko_user_code = f"EKO{user.id:06d}"
        
        # Save Eko user details
        eko_user, created = EkoUser.objects.get_or_create(
            user=user,
            defaults={
                'eko_user_code': mock_eko_user_code,
                'is_verified': True
            }
        )
        
        if not created:
            eko_user.eko_user_code = mock_eko_user_code
            eko_user.is_verified = True
            eko_user.save()
        
        # Create transaction record
        EkoTransaction.objects.create(
            user=user,
            transaction_type='onboard',
            client_ref_id=f"ONBRD{int(time.time())}",
            status='success',
            response_data={'eko_user_code': mock_eko_user_code}
        )
        
        logger.info(f"User onboarded successfully: {user.username}")
        
        return Response({
            'status': 'success',
            'message': 'User onboarded successfully with Eko',
            'eko_user_code': eko_user.eko_user_code
        })
    
    @action(detail=False, methods=['get'])
    def my_eko_info(self, request):
        """Get current user's Eko information"""
        try:
            eko_user = EkoUser.objects.get(user=request.user)
            serializer = EkoUserSerializer(eko_user)
            return Response({
                'status': 'success',
                'data': serializer.data
            })
        except EkoUser.DoesNotExist:
            return Response({
                'status': 'error',
                'message': 'User not onboarded with Eko',
                'onboarded': False
            })

class EkoDMTViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['post'])
    def validate_account(self, request):
        """Validate bank account - Production"""
        serializer = DMTValidateAccountSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        account_number = serializer.validated_data['account_number']
        ifsc_code = serializer.validated_data['ifsc_code']
        
        dmt_service = EkoDMTService(production=True)
        result = dmt_service.validate_bank_account(account_number, ifsc_code)
        
        return Response(result)
    
    @action(detail=False, methods=['post'])
    def add_recipient(self, request):
        """Add recipient for money transfer - Production"""
        serializer = DMTAddRecipientSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            eko_user = EkoUser.objects.get(user=request.user)
        except EkoUser.DoesNotExist:
            return Response({
                'status': 'error',
                'message': 'User not onboarded with Eko. Please onboard first.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        customer_mobile = request.user.phone_number
        
        if not customer_mobile:
            return Response({
                'status': 'error',
                'message': 'User mobile number is required for DMT services'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        dmt_service = EkoDMTService(production=True)
        result = dmt_service.add_recipient(
            customer_mobile=customer_mobile,
            account_number=serializer.validated_data['account_number'],
            ifsc_code=serializer.validated_data['ifsc_code'],
            recipient_name=serializer.validated_data['recipient_name'],
            recipient_mobile=serializer.validated_data['recipient_mobile'],
            bank_id=serializer.validated_data['bank_id']
        )
        
        # Save recipient information if successful
        if result.get('status') == 0:
            recipient_data = result.get('data', {})
            EkoRecipient.objects.create(
                user=request.user,
                recipient_id=recipient_data.get('recipient_id'),
                recipient_name=serializer.validated_data['recipient_name'],
                account_number=serializer.validated_data['account_number'],
                ifsc_code=serializer.validated_data['ifsc_code'],
                recipient_mobile=serializer.validated_data['recipient_mobile'],
                bank_name=dmt_service.get_bank_name_from_ifsc(serializer.validated_data['ifsc_code']),
                is_verified=True
            )
            logger.info(f"Recipient added successfully: {serializer.validated_data['recipient_name']}")
            
        return Response(result)
    
    @action(detail=False, methods=['get'])
    def get_recipients(self, request):
        """Get user's recipients"""
        try:
            recipients = EkoRecipient.objects.filter(user=request.user, is_verified=True)
            serializer = EkoRecipientSerializer(recipients, many=True)
            return Response({
                'status': 'success',
                'data': serializer.data
            })
        except Exception as e:
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def transfer_money(self, request):
        """Transfer money to recipient - Production"""
        serializer = DMTTransferMoneySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            eko_user = EkoUser.objects.get(user=request.user)
        except EkoUser.DoesNotExist:
            return Response({
                'status': 'error',
                'message': 'User not onboarded with Eko. Please onboard first.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        customer_mobile = request.user.phone_number
        
        if not customer_mobile:
            return Response({
                'status': 'error',
                'message': 'User mobile number is required for money transfer'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        with transaction.atomic():
            # Create transaction record
            client_ref_id = f"DMT{int(time.time())}"
            eko_transaction = EkoTransaction.objects.create(
                user=request.user,
                transaction_type='dmt',
                client_ref_id=client_ref_id,
                amount=serializer.validated_data['amount'],
                status='processing'
            )
            
            # Process money transfer
            dmt_service = EkoDMTService(production=True)
            result = dmt_service.initiate_transaction(
                customer_mobile=customer_mobile,
                recipient_id=serializer.validated_data['recipient_id'],
                amount=serializer.validated_data['amount'],
                channel=serializer.validated_data['channel'],
                client_ref_id=client_ref_id
            )
            
            # Update transaction
            eko_transaction.response_data = result
            
            if result.get('status') == 0:
                eko_transaction.status = 'success'
                eko_transaction.eko_reference_id = result.get('data', {}).get('tid')
                
                # Create wallet transaction
                Transaction.objects.create(
                    wallet=request.user.wallet,
                    amount=serializer.validated_data['amount'],
                    transaction_type='debit',
                    transaction_category='money_transfer',
                    description=f"DMT Transfer - Recipient ID: {serializer.validated_data['recipient_id']}",
                    created_by=request.user,
                    status='success'
                )
                
                logger.info(f"Money transfer successful: {client_ref_id}")
                
            else:
                eko_transaction.status = 'failed'
                logger.error(f"Money transfer failed: {result.get('message')}")
            
            eko_transaction.save()
            
            return Response({
                'status': 'success' if eko_transaction.status == 'success' else 'error',
                'transaction_id': str(eko_transaction.transaction_id),
                'client_ref_id': client_ref_id,
                'status': eko_transaction.status,
                'eko_reference': eko_transaction.eko_reference_id,
                'message': result.get('message', 'Transaction processed'),
                'data': result.get('data', {})
            })
    
    @action(detail=False, methods=['get'])
    def transaction_status(self, request):
        """Check transaction status"""
        transaction_id = request.query_params.get('transaction_id')
        inquiry_type = request.query_params.get('inquiry_type', 'client_ref')
        
        if not transaction_id:
            return Response({
                'status': 'error',
                'message': 'Transaction ID is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        dmt_service = EkoDMTService(production=True)
        result = dmt_service.transaction_inquiry(transaction_id, inquiry_type)
        
        return Response(result)
    
    @action(detail=False, methods=['get'])
    def check_balance(self, request):
        """Check Eko balance"""
        eko_service = EkoAPIService(production=True)
        result = eko_service.check_balance()
        
        return Response(result)

class EkoRechargeViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def operators(self, request):
        """Get available operators"""
        service_type = request.query_params.get('service_type', 'mobile')
        
        recharge_service = EkoRechargeService(production=True)
        result = recharge_service.get_operators(service_type)
        
        return Response(result)
    
    @action(detail=False, methods=['post'])
    def recharge(self, request):
        """Perform recharge"""
        serializer = RechargeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            eko_user = EkoUser.objects.get(user=request.user)
        except EkoUser.DoesNotExist:
            return Response({
                'status': 'error',
                'message': 'User not onboarded with Eko'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        with transaction.atomic():
            # Create transaction record
            client_ref_id = f"RECH{int(time.time())}"
            eko_transaction = EkoTransaction.objects.create(
                user=request.user,
                transaction_type='recharge',
                client_ref_id=client_ref_id,
                amount=serializer.validated_data['amount'],
                status='processing'
            )
            
            # Process recharge
            recharge_service = EkoRechargeService(production=True)
            result = recharge_service.recharge(
                mobile_number=serializer.validated_data['mobile_number'],
                operator_id=serializer.validated_data['operator_id'],
                amount=serializer.validated_data['amount'],
                circle=serializer.validated_data['circle']
            )
            
            # Update transaction
            eko_transaction.response_data = result
            
            if result.get('status') == 0:
                eko_transaction.status = 'success'
                eko_transaction.eko_reference_id = result.get('data', {}).get('transaction_id')
                
                # Create wallet transaction
                Transaction.objects.create(
                    wallet=request.user.wallet,
                    amount=serializer.validated_data['amount'],
                    transaction_type='debit',
                    transaction_category='recharge',
                    description=f"Mobile Recharge - {serializer.validated_data['mobile_number']}",
                    created_by=request.user,
                    status='success'
                )
                
            else:
                eko_transaction.status = 'failed'
            
            eko_transaction.save()
            
            return Response({
                'status': 'success' if eko_transaction.status == 'success' else 'error',
                'transaction_id': str(eko_transaction.transaction_id),
                'client_ref_id': client_ref_id,
                'status': eko_transaction.status,
                'eko_reference': eko_transaction.eko_reference_id,
                'message': result.get('message', 'Recharge processed'),
                'data': result.get('data', {})
            })

class EkoBBPSViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['post'])
    def fetch_bill(self, request):
        """Fetch bill details"""
        serializer = BBPSFetchBillSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        bbps_service = EkoBBPSService(production=True)
        result = bbps_service.fetch_bill(
            consumer_number=serializer.validated_data['consumer_number'],
            service_type=serializer.validated_data['service_type']
        )
        
        return Response(result)
    
    @action(detail=False, methods=['post'])
    def pay_bill(self, request):
        """Pay bill through Eko"""
        serializer = BBPSPayBillSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            eko_user = EkoUser.objects.get(user=request.user)
        except EkoUser.DoesNotExist:
            return Response({
                'status': 'error',
                'message': 'User not onboarded with Eko'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        with transaction.atomic():
            # Create transaction record
            client_ref_id = f"BBPS{int(time.time())}"
            eko_transaction = EkoTransaction.objects.create(
                user=request.user,
                transaction_type='bbps',
                client_ref_id=client_ref_id,
                amount=serializer.validated_data['amount'],
                status='processing'
            )
            
            # Process bill payment
            bbps_service = EkoBBPSService(production=True)
            result = bbps_service.pay_bill(
                consumer_number=serializer.validated_data['consumer_number'],
                service_provider=serializer.validated_data['service_provider'],
                amount=serializer.validated_data['amount'],
                bill_number=serializer.validated_data.get('bill_number')
            )
            
            # Update transaction
            eko_transaction.response_data = result
            
            if result.get('status') == 0:
                eko_transaction.status = 'success'
                eko_transaction.eko_reference_id = result.get('data', {}).get('transaction_id')
                
                # Create wallet transaction
                Transaction.objects.create(
                    wallet=request.user.wallet,
                    amount=serializer.validated_data['amount'],
                    transaction_type='debit',
                    transaction_category='bill_payment',
                    description=f"BBPS Payment - {serializer.validated_data['service_provider']}",
                    created_by=request.user,
                    status='success'
                )
                
            else:
                eko_transaction.status = 'failed'
            
            eko_transaction.save()
            
            return Response({
                'status': 'success' if eko_transaction.status == 'success' else 'error',
                'transaction_id': str(eko_transaction.transaction_id),
                'client_ref_id': client_ref_id,
                'status': eko_transaction.status,
                'eko_reference': eko_transaction.eko_reference_id,
                'message': result.get('message', 'Bill payment processed'),
                'data': result.get('data', {})
            })