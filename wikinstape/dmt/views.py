from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import transaction as db_transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from decimal import Decimal
import logging

from .models import DMTTransaction, DMTRecipient, DMTServiceCharge
from .serializers import (
    DMTTransactionSerializer, DMTRecipientSerializer, InitiateDMTSerializer,
    AddRecipientSerializer, VerifyCustomerSerializer, CalculateChargeSerializer
)
from .eko_service import EkoDMTService
from users.models import Wallet, Transaction

logger = logging.getLogger(__name__)

class DMTViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.eko_service = EkoDMTService()
    
    @action(detail=False, methods=['post'])
    def calculate_charge(self, request):
        """Calculate service charge for DMT transaction"""
        serializer = CalculateChargeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        amount = serializer.validated_data['amount']
        
        try:
            charge_config = DMTServiceCharge.objects.filter(
                amount_from__lte=amount,
                amount_to__gte=amount,
                is_active=True
            ).first()
            
            if not charge_config:
                return Response({
                    'error': 'No service charge configuration found for this amount'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            service_charge = charge_config.calculate_charge(amount)
            total_amount = amount + service_charge
            
            return Response({
                'amount': amount,
                'service_charge': service_charge,
                'total_amount': total_amount,
                'charge_config': {
                    'charge_type': charge_config.charge_type,
                    'charge_value': charge_config.charge_value,
                    'min_charge': charge_config.min_charge,
                    'max_charge': charge_config.max_charge
                }
            })
            
        except Exception as e:
            logger.error(f"Error calculating charge: {str(e)}")
            return Response({
                'error': 'Failed to calculate service charge'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['post'])
    def check_customer(self, request):
        """Check if customer exists on EKO platform"""
        customer_mobile = request.data.get('customer_mobile')
        
        if not customer_mobile:
            return Response({
                'error': 'Customer mobile number is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            result = self.eko_service.check_customer(customer_mobile)
            
            if result['success']:
                return Response({
                    'exists': result['exists'],
                    'customer_data': result['data'],
                    'message': result['message']
                })
            else:
                return Response({
                    'error': result.get('error', 'Failed to check customer'),
                    'exists': False
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            logger.error(f"Error checking customer: {str(e)}")
            return Response({
                'error': 'Failed to check customer status'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['post'])
    def create_customer(self, request):
        """Create new customer on EKO platform"""
        customer_mobile = request.data.get('customer_mobile')
        name = request.data.get('name')
        email = request.data.get('email', '')
        
        if not customer_mobile or not name:
            return Response({
                'error': 'Customer mobile and name are required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            result = self.eko_service.create_customer(customer_mobile, name, email)
            
            if result['success']:
                return Response({
                    'success': True,
                    'customer_id': result.get('customer_id'),
                    'message': result['message'],
                    'data': result['data']
                })
            else:
                return Response({
                    'error': result.get('error', 'Failed to create customer'),
                    'success': False
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            logger.error(f"Error creating customer: {str(e)}")
            return Response({
                'error': 'Failed to create customer'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['post'])
    def verify_customer(self, request):
        """Verify customer with OTP"""
        serializer = VerifyCustomerSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        customer_mobile = serializer.validated_data['customer_mobile']
        otp = serializer.validated_data['otp']
        
        try:
            result = self.eko_service.verify_customer(customer_mobile, otp)
            
            if result['success']:
                return Response({
                    'success': True,
                    'message': result['message'],
                    'data': result['data']
                })
            else:
                return Response({
                    'error': result.get('error', 'Failed to verify customer'),
                    'success': False
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            logger.error(f"Error verifying customer: {str(e)}")
            return Response({
                'error': 'Failed to verify customer'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['post'])
    def add_recipient(self, request):
        """Add recipient for money transfer"""
        serializer = AddRecipientSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        data = serializer.validated_data
        
        try:
            result = self.eko_service.add_recipient(data['customer_mobile'], data)
            
            if result['success']:
                recipient = DMTRecipient.objects.create(
                    customer=request.user,
                    recipient_id=result.get('recipient_id'),
                    name=data['name'],
                    mobile=data['mobile'],
                    account_number=data['account_number'],
                    ifsc_code=data['ifsc_code'],
                    bank_name='', 
                    bank_id=data['bank_id'],
                    is_verified=result.get('data', {}).get('is_verified', False)
                )
                
                return Response({
                    'success': True,
                    'recipient_id': result.get('recipient_id'),
                    'message': result['message'],
                    'recipient': DMTRecipientSerializer(recipient).data
                })
            else:
                return Response({
                    'error': result.get('error', 'Failed to add recipient'),
                    'success': False
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            logger.error(f"Error adding recipient: {str(e)}")
            return Response({
                'error': 'Failed to add recipient'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'])
    def get_recipients(self, request):
        """Get recipients for a customer"""
        customer_mobile = request.query_params.get('customer_mobile')
        
        if not customer_mobile:
            return Response({
                'error': 'Customer mobile number is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            result = self.eko_service.get_recipients(customer_mobile)
            
            if result['success']:
                local_recipients = DMTRecipient.objects.filter(
                    customer=request.user,
                    is_active=True
                )
                
                return Response({
                    'success': True,
                    'eko_recipients': result.get('recipients', []),
                    'local_recipients': DMTRecipientSerializer(local_recipients, many=True).data
                })
            else:
                return Response({
                    'error': result.get('error', 'Failed to get recipients'),
                    'success': False
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            logger.error(f"Error getting recipients: {str(e)}")
            return Response({
                'error': 'Failed to get recipients'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['post'])
    @db_transaction.atomic
    def initiate_transfer(self, request):
        """Initiate money transfer with complete flow"""
        serializer = InitiateDMTSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        data = serializer.validated_data
        user = request.user
        wallet = user.wallet
        
        try:
            charge_config = DMTServiceCharge.objects.filter(
                amount_from__lte=data['amount'],
                amount_to__gte=data['amount'],
                is_active=True
            ).first()
            
            if not charge_config:
                return Response({
                    'error': 'No service charge configuration found'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            service_charge = charge_config.calculate_charge(data['amount'])
            total_amount = data['amount'] + service_charge
            
            if not wallet.verify_pin(data['pin']):
                return Response({
                    'error': 'Invalid wallet PIN'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            if not wallet.has_sufficient_balance(total_amount):
                return Response({
                    'error': 'Insufficient wallet balance'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            dmt_transaction = DMTTransaction.objects.create(
                user=user,
                customer_mobile=data['customer_mobile'],
                recipient_id=data['recipient_id'],
                amount=data['amount'],
                service_charge=service_charge,
                total_amount=total_amount,
                channel=data['channel'],
                latlong=data.get('latlong', ''),
                status='initiated'
            )
            
            transaction_data = {
                'customer_mobile': data['customer_mobile'],
                'recipient_id': data['recipient_id'],
                'amount': int(data['amount']),
                'channel': 1 if data['channel'] == 'neft' else 2,
                'client_ref_id': dmt_transaction.client_ref_id,
                'latlong': data.get('latlong', '')
            }
            
            result = self.eko_service.initiate_transaction(transaction_data)
            
            if result['success']:
                wallet.deduct_amount(total_amount, 0, data['pin'])
                
                dmt_transaction.eko_transaction_id = result.get('transaction_id')
                dmt_transaction.eko_status = result.get('tx_status')
                dmt_transaction.status = self._get_transaction_status(result.get('tx_status'))
                dmt_transaction.processed_at = timezone.now()
                dmt_transaction.save()
                
                Transaction.objects.create(
                    wallet=wallet,
                    amount=total_amount,
                    net_amount=total_amount,
                    service_charge=0,
                    transaction_type='debit',
                    transaction_category='money_transfer',
                    description=f"DMT Transfer to {data['recipient_id']}",
                    created_by=user,
                    status='success'
                )
                
                return Response({
                    'success': True,
                    'transaction_id': dmt_transaction.reference_number,
                    'eko_transaction_id': dmt_transaction.eko_transaction_id,
                    'status': dmt_transaction.status,
                    'message': 'Transaction initiated successfully',
                    'data': DMTTransactionSerializer(dmt_transaction).data
                })
            else:
                dmt_transaction.status = 'failed'
                dmt_transaction.response_message = result.get('error', 'EKO API error')
                dmt_transaction.save()
                
                return Response({
                    'error': result.get('error', 'Failed to initiate transaction'),
                    'success': False
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            logger.error(f"Error initiating transfer: {str(e)}")
            return Response({
                'error': 'Failed to initiate money transfer'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['post'])
    def check_transaction_status(self, request):
        """Check transaction status"""
        transaction_id = request.data.get('transaction_id')
        reference_number = request.data.get('reference_number')
        
        if not transaction_id and not reference_number:
            return Response({
                'error': 'Transaction ID or reference number is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            if transaction_id:
                transaction = get_object_or_404(DMTTransaction, eko_transaction_id=transaction_id)
            else:
                transaction = get_object_or_404(DMTTransaction, reference_number=reference_number)
            
            result = self.eko_service.check_transaction_status(transaction.eko_transaction_id)
            
            if result['success']:
                transaction.eko_status = result.get('tx_status')
                transaction.status = self._get_transaction_status(result.get('tx_status'))
                transaction.utr_number = result.get('utr_number')
                
                if transaction.status in ['success', 'failed', 'refunded']:
                    transaction.completed_at = timezone.now()
                
                transaction.save()
                
                return Response({
                    'success': True,
                    'status': transaction.status,
                    'eko_status': transaction.eko_status,
                    'utr_number': transaction.utr_number,
                    'message': result.get('message', ''),
                    'transaction': DMTTransactionSerializer(transaction).data
                })
            else:
                return Response({
                    'error': result.get('error', 'Failed to check transaction status'),
                    'success': False
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            logger.error(f"Error checking transaction status: {str(e)}")
            return Response({
                'error': 'Failed to check transaction status'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'])
    def transaction_history(self, request):
        """Get DMT transaction history for user"""
        try:
            transactions = DMTTransaction.objects.filter(user=request.user).order_by('-initiated_at')
            
            status_filter = request.query_params.get('status')
            if status_filter:
                transactions = transactions.filter(status=status_filter)
            
            start_date = request.query_params.get('start_date')
            end_date = request.query_params.get('end_date')
            if start_date and end_date:
                transactions = transactions.filter(initiated_at__date__range=[start_date, end_date])
            
            page = self.paginate_queryset(transactions)
            if page is not None:
                serializer = DMTTransactionSerializer(page, many=True)
                return self.get_paginated_response(serializer.data)
            
            serializer = DMTTransactionSerializer(transactions, many=True)
            return Response({
                'transactions': serializer.data,
                'total_count': transactions.count()
            })
            
        except Exception as e:
            logger.error(f"Error getting transaction history: {str(e)}")
            return Response({
                'error': 'Failed to get transaction history'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _get_transaction_status(self, eko_status):
        """Map EKO status to local status"""
        status_map = {
            0: 'success',
            1: 'failed', 
            2: 'pending',
            3: 'refund_pending',
            4: 'refunded',
            5: 'hold'
        }
        return status_map.get(eko_status, 'pending')

class DMTRecipientViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = DMTRecipientSerializer
    
    def get_queryset(self):
        return DMTRecipient.objects.filter(customer=self.request.user, is_active=True)
    
    def perform_create(self, serializer):
        serializer.save(customer=self.request.user)