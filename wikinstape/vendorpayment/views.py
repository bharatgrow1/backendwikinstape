from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction as db_transaction
from django.utils import timezone
from users.models import Transaction
from decimal import Decimal
import logging
import json

from .serializers import VendorPaymentSerializer, VendorPaymentResponseSerializer
from .services.vendor_manager import vendor_manager
from .models import VendorPayment

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
            
            # ✅ STEP 1: Create VendorPayment record BEFORE processing
            vendor_payment = VendorPayment.objects.create(
                user=user,
                recipient_name=data['recipient_name'],
                recipient_account=data['account'],
                recipient_ifsc=data['ifsc'],
                amount=amount,
                processing_fee=fee,
                gst=gst,
                total_fee=total_fee,
                total_deduction=total_deduction,
                purpose=data.get('purpose', 'Vendor Payment'),
                remarks=data.get('remarks', ''),
                payment_mode=data['payment_mode'],
                status='initiated'
            )
            
            # ✅ STEP 2: Deduct from wallet
            wallet.deduct_amount(amount, total_fee, pin)
            
            # ✅ STEP 3: Create wallet transaction
            wallet_transaction = Transaction.objects.create(
                wallet=wallet,
                amount=amount,
                service_charge=total_fee,
                net_amount=amount,
                transaction_type='debit',
                transaction_category='vendor_payment',
                description=f"Vendor payment to {data['recipient_name']}",
                created_by=user,
                status='success',
                metadata={
                    'vendor_payment_id': vendor_payment.id,
                    'recipient_account': data['account'],
                    'ifsc': data['ifsc']
                }
            )
            
            logger.info(f"✅ Wallet deduction successful: ₹{total_deduction} from {user.username}")
            
        except Exception as e:
            logger.error(f"❌ Wallet deduction failed: {str(e)}")
            return Response({
                'status': 1,
                'message': f'Payment failed: {str(e)}'
            })
        
        try:
            # ✅ STEP 4: Initiate EKO payment
            eko_data = data.copy()
            eko_result = vendor_manager.initiate_payment(eko_data)
            
            logger.info(f"✅ EKO vendor payment response: {eko_result}")
            
            eko_status = eko_result.get('status', 1)
            eko_message = eko_result.get('message', '')
            eko_data_response = eko_result.get('data', {})
            
            # ✅ STEP 5: Update VendorPayment record with EKO response
            vendor_payment.eko_tid = eko_data_response.get('tid')
            vendor_payment.client_ref_id = eko_data_response.get('client_ref_id', vendor_payment.client_ref_id)
            vendor_payment.bank_ref_num = eko_data_response.get('bank_ref_num', '')
            vendor_payment.timestamp = eko_data_response.get('timestamp', '')
            
            if eko_status != 0:
                # Payment failed, refund and update status
                vendor_payment.status = 'failed'
                vendor_payment.status_message = eko_message
                vendor_payment.save()
                
                wallet.add_amount(amount)
                Transaction.objects.create(
                    wallet=wallet,
                    amount=amount,
                    transaction_type='credit',
                    transaction_category='refund',
                    description=f"Refund for failed vendor payment to {data['recipient_name']}",
                    created_by=user,
                    status='success',
                    metadata={'vendor_payment_id': vendor_payment.id}
                )
                
                return Response({
                    'status': 1,
                    'message': f'Vendor payment failed: {eko_message}. Amount refunded.',
                    'payment_id': vendor_payment.id
                })
            
            # ✅ STEP 6: Payment successful, update status
            vendor_payment.status = 'success'
            vendor_payment.status_message = 'Payment initiated successfully'
            vendor_payment.save()
            
            response_data = {
                'status': 0,
                'message': 'Vendor payment initiated successfully',
                'payment_id': vendor_payment.id,
                'receipt_number': vendor_payment.receipt_number,
                'data': {
                    'tid': eko_data_response.get('tid'),
                    'client_ref_id': vendor_payment.client_ref_id,
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
                    'amount': str(amount),
                    'total_deduction': str(total_deduction)
                }
            }
            
            return Response(response_data)
            
        except Exception as e:
            logger.error(f"❌ EKO payment failed: {str(e)}")
            # Update vendor payment status to failed
            vendor_payment.status = 'failed'
            vendor_payment.status_message = str(e)
            vendor_payment.save()
            
            try:
                wallet.add_amount(amount)
                Transaction.objects.create(
                    wallet=wallet,
                    amount=amount,
                    transaction_type='credit',
                    transaction_category='refund',
                    description=f"Refund for failed vendor payment (EKO error) to {data['recipient_name']}",
                    created_by=user,
                    status='success',
                    metadata={'vendor_payment_id': vendor_payment.id}
                )
            except Exception as refund_error:
                logger.error(f"❌ Refund failed: {str(refund_error)}")
            
            return Response({
                'status': 1,
                'message': f'Vendor payment failed: {str(e)}. Please contact support.',
                'payment_id': vendor_payment.id
            })
    
    @action(detail=False, methods=['get'])
    def history(self, request):
        """Get vendor payment history for current user"""
        payments = VendorPayment.objects.filter(user=request.user).order_by('-created_at')
        serializer = VendorPaymentResponseSerializer(payments, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def receipt(self, request, pk=None):
        """Generate receipt for vendor payment"""
        try:
            payment = VendorPayment.objects.get(id=pk, user=request.user)
            
            # Mark receipt as generated
            if not payment.is_receipt_generated:
                payment.is_receipt_generated = True
                payment.receipt_generated_at = timezone.now()
                payment.save()
            
            receipt_data = payment.generate_receipt_data()
            
            return Response({
                'status': 0,
                'message': 'Receipt generated successfully',
                'receipt_data': receipt_data,
                'download_url': f'/api/vendor-payment/{payment.id}/download-receipt/'
            })
        except VendorPayment.DoesNotExist:
            return Response({
                'status': 1,
                'message': 'Payment not found'
            }, status=404)
    
    @action(detail=True, methods=['get'])
    def download_receipt(self, request, pk=None):
        """Download receipt as PDF"""
        # You'll need to implement PDF generation here
        # Using libraries like reportlab, weasyprint, or xhtml2pdf
        pass