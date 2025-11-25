from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import transaction
from django.shortcuts import get_object_or_404
import decimal
import json
from .models import EkoUser, EkoService, EkoTransaction
from .serializers import *
from .service_handlers import EkoBBPSService, EkoRechargeService, EkoMoneyTransferService
from .eko_service import EkoAPIService
from users.models import User, Transaction
import time 
from datetime import datetime 


def make_json_serializable(data):
    """Convert Decimal objects to float for JSON serialization"""
    if isinstance(data, dict):
        return {k: make_json_serializable(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [make_json_serializable(item) for item in data]
    elif isinstance(data, decimal.Decimal):
        return float(data)
    else:
        return data
    

class EkoUserViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['post'])
    def onboard(self, request):
        """Onboard user to Eko platform"""
        serializer = EkoOnboardSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user_id = serializer.validated_data['user_id']
        user = get_object_or_404(User, id=user_id)
        
        # Check if already onboarded
        if hasattr(user, 'eko_user') and user.eko_user.is_verified:
            return Response({
                'message': 'User already onboarded with Eko',
                'eko_user_code': user.eko_user.eko_user_code
            })
        
        # Prepare user data for Eko onboarding
        user_data = {
            'pan_number': user.pan_number or '',
            'phone_number': user.phone_number or '',
            'first_name': user.first_name or '',
            'last_name': user.last_name or '',
            'email': user.email or '',
            'address': user.address or '',
            'city': user.city or '',
            'state': user.state or '',
            'pincode': user.pincode or '',
            'landmark': user.landmark or '',
            'date_of_birth': user.date_of_birth,
            'business_name': user.business_name or ''
        }
        
        eko_service = EkoAPIService()
        result = eko_service.onboard_user(user_data)
        
        if result.get('status') == 0:
            # Save Eko user details
            eko_user, created = EkoUser.objects.get_or_create(
                user=user,
                defaults={
                    'eko_user_code': result['data']['user_code'],
                    'is_verified': True
                }
            )
            
            if not created:
                eko_user.eko_user_code = result['data']['user_code']
                eko_user.is_verified = True
                eko_user.save()
            
            return Response({
                'message': 'User onboarded successfully',
                'eko_user_code': eko_user.eko_user_code
            })
        else:
            return Response({
                'error': result.get('message', 'Onboarding failed')
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def my_eko_info(self, request):
        """Get current user's Eko information"""
        try:
            eko_user = EkoUser.objects.get(user=request.user)
            serializer = EkoUserSerializer(eko_user)
            return Response(serializer.data)
        except EkoUser.DoesNotExist:
            return Response({
                'message': 'User not onboarded with Eko',
                'onboarded': False
            })

class EkoBBPSViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['post'])
    def fetch_bill(self, request):
        """Fetch bill details"""
        serializer = BBPSFetchBillSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        consumer_number = serializer.validated_data['consumer_number']
        service_type = serializer.validated_data['service_type']
        
        bbps_service = EkoBBPSService()
        result = bbps_service.fetch_bill(consumer_number, service_type)
        
        return Response(result)
    
    @action(detail=False, methods=['post'])
    def pay_bill(self, request):
        """Pay bill through Eko"""
        serializer = BBPSPayBillSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Get user's Eko details
        try:
            eko_user = EkoUser.objects.get(user=request.user)
        except EkoUser.DoesNotExist:
            return Response({
                'error': 'User not onboarded with Eko. Please onboard first.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        consumer_number = serializer.validated_data['consumer_number']
        service_provider = serializer.validated_data['service_provider']
        amount = serializer.validated_data['amount']
        bill_number = serializer.validated_data.get('bill_number')
        
        # Get Eko service mapping
        try:
            eko_service = EkoService.objects.get(
                service_subcategory__name__icontains=service_provider.lower()
            )
        except EkoService.DoesNotExist:
            return Response({
                'error': 'Service not configured for Eko'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        with transaction.atomic():
            # Create transaction record
            eko_transaction = EkoTransaction.objects.create(
                user=request.user,
                eko_service=eko_service,
                client_ref_id=f"BBPS{int(time.time())}",
                amount=amount,
                status='processing'
            )
            
            # Process payment
            bbps_service = EkoBBPSService()
            result = bbps_service.pay_bill(
                eko_user.eko_user_code,
                consumer_number,
                service_provider,
                amount,
                bill_number
            )
            
            # Update transaction
            eko_transaction.response_data = result
            if result.get('status') == 0:
                eko_transaction.status = 'success'
                eko_transaction.eko_reference_id = result['data'].get('transaction_id')
                
                # Create wallet transaction
                from users.models import Transaction
                Transaction.objects.create(
                    wallet=request.user.wallet,
                    amount=amount,
                    transaction_type='debit',
                    transaction_category='bill_payment',
                    description=f"BBPS Payment - {service_provider}",
                    created_by=request.user,
                    status='success'
                )
                
                # Process commission
                self.process_commission(request.user, amount, 'bbps_payment')
                
            else:
                eko_transaction.status = 'failed'
            
            eko_transaction.save()
            
            return Response({
                'transaction_id': eko_transaction.transaction_id,
                'status': eko_transaction.status,
                'eko_reference': eko_transaction.eko_reference_id,
                'message': result.get('message')
            })

class EkoRechargeViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def operators(self, request):
        """Get available operators"""
        service_type = request.query_params.get('service_type', 'mobile')
        
        recharge_service = EkoRechargeService()
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
                'error': 'User not onboarded with Eko'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        mobile_number = serializer.validated_data['mobile_number']
        operator_id = serializer.validated_data['operator_id']
        amount = serializer.validated_data['amount']
        circle = serializer.validated_data['circle']
        
        # Get Eko service
        try:
            eko_service = EkoService.objects.get(eko_service_code='RECHARGE')
        except EkoService.DoesNotExist:
            return Response({
                'error': 'Recharge service not configured'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        with transaction.atomic():
            # Create transaction record
            eko_transaction = EkoTransaction.objects.create(
                user=request.user,
                eko_service=eko_service,
                client_ref_id=f"RECH{int(time.time())}",
                amount=amount,
                status='processing'
            )
            
            # Process recharge
            recharge_service = EkoRechargeService()
            result = recharge_service.recharge(
                eko_user.eko_user_code,
                mobile_number,
                operator_id,
                amount,
                circle
            )
            
            # Update transaction
            eko_transaction.response_data = result
            if result.get('status') == 0:
                eko_transaction.status = 'success'
                eko_transaction.eko_reference_id = result['data'].get('transaction_id')
                
                # Create wallet transaction
                from users.models import Transaction
                Transaction.objects.create(
                    wallet=request.user.wallet,
                    amount=amount,
                    transaction_type='debit',
                    transaction_category='recharge',
                    description=f"Mobile Recharge - {mobile_number}",
                    created_by=request.user,
                    status='success'
                )
                
                # Process commission
                self.process_commission(request.user, amount, 'recharge')
                
            else:
                eko_transaction.status = 'failed'
            
            eko_transaction.save()
            
            return Response({
                'transaction_id': eko_transaction.transaction_id,
                'status': eko_transaction.status,
                'eko_reference': eko_transaction.eko_reference_id,
                'message': result.get('message')
            })

class EkoMoneyTransferViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['post'])
    def transfer(self, request):
        """Transfer money with PROPER error handling"""
        serializer = MoneyTransferSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            eko_user = EkoUser.objects.get(user=request.user)
        except EkoUser.DoesNotExist:
            return Response({
                'error': 'User not onboarded with Eko. Please onboard first.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get Eko service
        try:
            eko_service = EkoService.objects.get(eko_service_code='MONEY_TRANSFER')
        except EkoService.DoesNotExist:
            return Response({
                'error': 'Money transfer service not configured'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Process transfer
        try:
            transfer_service = EkoMoneyTransferService()
            
            # Pehle service activation check karein
            activation_result = transfer_service.activate_money_transfer_service(eko_user.eko_user_code)
            print(f"Service Activation: {activation_result}")
            
            # Phir transfer karein
            result = transfer_service.transfer_money(
                eko_user.eko_user_code,
                {
                    'account_number': serializer.validated_data['account_number'],
                    'ifsc_code': serializer.validated_data['ifsc_code'],
                    'recipient_name': serializer.validated_data['recipient_name']
                },
                serializer.validated_data['amount'],
                serializer.validated_data['payment_mode']
            )
            
            # Create transaction record
            eko_transaction = EkoTransaction.objects.create(
                user=request.user,
                eko_service=eko_service,
                client_ref_id=f"MT{int(time.time())}",
                amount=serializer.validated_data['amount'],
                status='success' if result.get('status') == 0 else 'failed',
                eko_reference_id=result.get('data', {}).get('transaction_id'),
                response_data=result
            )
            
            # Handle response
            if result.get('status') == 0:
                # Create wallet transaction
                Transaction.objects.create(
                    wallet=request.user.wallet,
                    amount=serializer.validated_data['amount'],
                    transaction_type='debit',
                    transaction_category='money_transfer',
                    description=f"Money Transfer to {serializer.validated_data['recipient_name']}",
                    created_by=request.user,
                    status='success'
                )
                
                return Response({
                    'status': 'success',
                    'transaction_id': str(eko_transaction.transaction_id),
                    'eko_reference': eko_transaction.eko_reference_id,
                    'message': result.get('message', 'Money transferred successfully'),
                    'data': result.get('data', {})
                })
            else:
                return Response({
                    'status': 'error',
                    'transaction_id': str(eko_transaction.transaction_id),
                    'message': result.get('message', 'Money transfer failed'),
                    'details': result
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            return Response({
                'status': 'error',
                'message': f'Transfer failed: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['post'])
    def activate_service(self, request):
        """Activate money transfer service manually"""
        try:
            eko_user = EkoUser.objects.get(user=request.user)
        except EkoUser.DoesNotExist:
            return Response({
                'error': 'User not onboarded with Eko'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            transfer_service = EkoMoneyTransferService()
            result = transfer_service.activate_money_transfer_service(eko_user.eko_user_code)
            
            return Response({
                'status': 'success' if result.get('status') == 0 else 'error',
                'message': result.get('message', 'Service activation completed'),
                'details': result
            })
                
        except Exception as e:
            return Response({
                'status': 'error',
                'message': f'Service activation failed: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)