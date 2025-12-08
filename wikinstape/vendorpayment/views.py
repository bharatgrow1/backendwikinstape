from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction as db_transaction
from django.utils import timezone
from users.models import Transaction
from decimal import Decimal
import logging

from .serializers import VendorPaymentSerializer
from .services.vendor_manager import vendor_manager

logger = logging.getLogger(__name__)

class VendorPaymentViewSet(viewsets.ViewSet):

    @action(detail=False, methods=["post"])
    @db_transaction.atomic
    def pay(self, request):
        serializer = VendorPaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = request.user
        data = serializer.validated_data
        
        pin = request.data.get('pin')
        if not pin:
            return Response({
                'status': 1,
                'message': 'Wallet PIN is required'
            })
        
        try:
            wallet = user.wallet
            
            if not wallet.verify_pin(pin):
                return Response({
                    'status': 1,
                    'message': 'Invalid wallet PIN'
                })
            
            amount = Decimal(str(data['amount']))
            fee = Decimal('7.00')
            gst = Decimal('1.26')
            total_fee = Decimal('8.26')
            total_deduction = amount + total_fee
            
            if wallet.balance < total_deduction:
                return Response({
                    'status': 1,
                    'message': f'Insufficient wallet balance. Required: ₹{total_deduction}, Available: ₹{wallet.balance}'
                })
            
            wallet.deduct_amount(amount, total_fee, pin)
            
            wallet_transaction = Transaction.objects.create(
                wallet=wallet,
                amount=amount,
                service_charge=total_fee,
                net_amount=amount,
                transaction_type='debit',
                transaction_category='vendor_payment',
                description=f"Vendor payment to {data['recipient_name']}",
                created_by=user,
                status='success'
            )
            
            logger.info(f"✅ Wallet deduction successful: ₹{total_deduction} from {user.username}")
            
        except Exception as e:
            logger.error(f"❌ Wallet deduction failed: {str(e)}")
            return Response({
                'status': 1,
                'message': f'Payment failed: {str(e)}'
            })
        
        try:
            eko_data = data.copy()
            eko_result = vendor_manager.initiate_payment(eko_data)
            
            logger.info(f"✅ EKO vendor payment response: {eko_result}")
            
            eko_status = eko_result.get('status', 1)
            eko_message = eko_result.get('message', '')
            eko_data_response = eko_result.get('data', {})
            
            if eko_status != 0:
                wallet.add_amount(amount)
                Transaction.objects.create(
                    wallet=wallet,
                    amount=amount,
                    transaction_type='credit',
                    transaction_category='refund',
                    description=f"Refund for failed vendor payment to {data['recipient_name']}",
                    created_by=user,
                    status='success'
                )
                
                return Response({
                    'status': 1,
                    'message': f'Vendor payment failed: {eko_message}. Amount refunded.'
                })
            
            response_data = {
                'status': 0,
                'message': 'Vendor payment initiated successfully',
                'data': {
                    'tid': eko_data_response.get('tid'),
                    'client_ref_id': eko_data_response.get('client_ref_id'),
                    'fee': str(fee),
                    'gst': str(gst),
                    'totalfee': str(total_fee),
                    'balance': str(wallet.balance),
                    'recipient_name': data['recipient_name'],
                    'ifsc': data['ifsc'],
                    'bank_ref_num': eko_data_response.get('bank_ref_num', ''),
                    'account': data['account'],
                    'txstatus_desc': eko_data_response.get('txstatus_desc', 'Initiated'),
                    'timestamp': eko_data_response.get('timestamp', ''),
                    'amount': str(amount)
                }
            }
            
            return Response(response_data)
            
        except Exception as e:
            logger.error(f"❌ EKO payment failed: {str(e)}")
            try:
                wallet.add_amount(amount)
                Transaction.objects.create(
                    wallet=wallet,
                    amount=amount,
                    transaction_type='credit',
                    transaction_category='refund',
                    description=f"Refund for failed vendor payment (EKO error) to {data['recipient_name']}",
                    created_by=user,
                    status='success'
                )
            except Exception as refund_error:
                logger.error(f"❌ Refund failed: {str(refund_error)}")
            
            return Response({
                'status': 1,
                'message': f'Vendor payment failed: {str(e)}. Please contact support.'
            })