from rest_framework import viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.db import transaction as db_transaction
from django.utils import timezone
from users.models import Transaction
from decimal import Decimal
import logging
from vendorpayment.models import VendorPayment 
from vendorpayment.serializers import VendorPaymentSerializer
from vendorpayment.services.vendor_manager import vendor_manager
from .services.receipt_generator import VendorReceiptGenerator

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
            
            # ✅ FIXED: Calculate total deduction properly
            amount = Decimal(str(data['amount']))  # ₹10.00
            fee = Decimal('7.00')  # Processing fee
            gst = Decimal('1.26')  # GST
            total_fee = fee + gst  # ₹8.26
            total_deduction = amount + total_fee  # ₹10.00 + ₹8.26 = ₹18.26
            
            logger.info(f"💰 Payment Calculation:")
            logger.info(f"   Transfer Amount: ₹{amount}")
            logger.info(f"   Processing Fee: ₹{fee}")
            logger.info(f"   GST: ₹{gst}")
            logger.info(f"   Total Fee: ₹{total_fee}")
            logger.info(f"   Total Deduction: ₹{total_deduction}")
            logger.info(f"   Wallet Balance: ₹{wallet.balance}")
            
            if wallet.balance < total_deduction:
                return Response({
                    'status': 1,
                    'message': f'Insufficient wallet balance. Required: ₹{total_deduction} (₹{amount} transfer + ₹{total_fee} fees), Available: ₹{wallet.balance}'
                })
            
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
            
            wallet.deduct_amount(amount, total_fee, pin)
            
            transaction = Transaction.objects.create(
                wallet=wallet,
                amount=amount,
                service_charge=total_fee,
                net_amount=amount,
                transaction_type='debit',
                transaction_category='vendor_payment',
                description=f"Vendor payment to {data['recipient_name']} - Account: {data['account'][-4:]}",
                created_by=user,
                status='success',
                metadata={
                    'vendor_payment_id': vendor_payment.id,
                    'recipient_name': data['recipient_name'],
                    'recipient_account': data['account'][-4:],
                    'ifsc': data['ifsc'],
                    'transfer_amount': str(amount),
                    'fee': str(total_fee),
                    'total_deduction': str(total_deduction)
                }
            )
            
            logger.info(f"✅ Wallet deduction successful: ₹{total_deduction} deducted from wallet")
            logger.info(f"✅ New wallet balance: ₹{wallet.balance}")
            
        except Exception as e:
            logger.error(f"❌ Wallet deduction failed: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return Response({
                'status': 1,
                'message': f'Payment failed: {str(e)}'
            })
        
        try:
            eko_data = data.copy()
            eko_data['amount'] = str(amount)
            
            logger.info(f"📤 Sending to EKO: Transfer Amount = ₹{amount}")
            eko_result = vendor_manager.initiate_payment(eko_data, vendor_payment.id)
            
            logger.info(f"✅ EKO vendor payment response: {eko_result}")
            
            eko_status = eko_result.get('status', 1)
            eko_message = eko_result.get('message', '')
            eko_data_response = eko_result.get('data', {})
            
            vendor_payment.refresh_from_db()
            vendor_payment.eko_tid = eko_data_response.get('tid')
            vendor_payment.client_ref_id = eko_data_response.get('client_ref_id', vendor_payment.client_ref_id)
            vendor_payment.bank_ref_num = eko_data_response.get('bank_ref_num', '')
            vendor_payment.timestamp = eko_data_response.get('timestamp', '')
            
            if eko_status != 0:
                vendor_payment.status = 'failed'
                vendor_payment.status_message = eko_message
                vendor_payment.save()
                
                wallet.add_amount(total_deduction) 
                Transaction.objects.create(
                    wallet=wallet,
                    amount=total_deduction, 
                    transaction_type='credit',
                    transaction_category='refund',
                    description=f"Refund for failed vendor payment to {data['recipient_name']}",
                    created_by=user,
                    status='success',
                    metadata={'vendor_payment_id': vendor_payment.id}
                )
                
                return Response({
                    'status': 1,
                    'message': f'Vendor payment failed: {eko_message}. ₹{total_deduction} refunded to wallet.',
                    'payment_id': vendor_payment.id
                })
            
            vendor_payment.status = 'success'
            vendor_payment.status_message = 'Payment initiated successfully'
            vendor_payment.save()
            
            if not vendor_payment.receipt_number:
                vendor_payment.receipt_number = f"VP{vendor_payment.id:08d}"
                vendor_payment.save(update_fields=['receipt_number'])
            
            response_data = {
                'status': 0,
                'message': 'Vendor payment initiated successfully',
                'payment_id': vendor_payment.id,
                'receipt_number': vendor_payment.receipt_number,
                'data': {
                    'transfer_amount': str(amount),
                    'fee': str(fee),
                    'gst': str(gst),
                    'total_fee': str(total_fee),
                    'total_deduction': str(total_deduction),
                    'balance': str(wallet.balance),
                    'recipient_name': data['recipient_name'],
                    'account': data['account'][-4:],
                    'ifsc': data['ifsc'],
                    'bank_ref_num': eko_data_response.get('bank_ref_num', ''),
                    'status': eko_data_response.get('txstatus_desc', 'Initiated'),
                    'transaction_id': vendor_payment.client_ref_id,
                    'timestamp': eko_data_response.get('timestamp', ''),
                    'purpose': data.get('purpose', 'Vendor Payment'),
                    'payment_mode': data['payment_mode']
                }
            }
            
            logger.info(f"✅ Final response: {response_data}")
            return Response(response_data)
            
        except Exception as e:
            logger.error(f"❌ EKO payment failed: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            
            vendor_payment.status = 'failed'
            vendor_payment.status_message = str(e)
            vendor_payment.save()
            
            wallet.add_amount(total_deduction)
            Transaction.objects.create(
                wallet=wallet,
                amount=total_deduction,
                transaction_type='credit',
                transaction_category='refund',
                description=f"Refund for failed vendor payment (EKO error) to {data['recipient_name']}",
                created_by=user,
                status='success',
                metadata={'vendor_payment_id': vendor_payment.id}
            )
            
            return Response({
                'status': 1,
                'message': f'Vendor payment failed: {str(e)}. ₹{total_deduction} refunded.',
                'payment_id': vendor_payment.id
            })
        


    @action(detail=False, methods=['get'])
    def my_payments(self, request):
        """Get current user's payment history"""
        try:
            # Get query parameters
            status_filter = request.query_params.get('status', '')
            start_date = request.query_params.get('start_date', '')
            end_date = request.query_params.get('end_date', '')
            search = request.query_params.get('search', '')
            page = int(request.query_params.get('page', 1))
            limit = int(request.query_params.get('limit', 20))
            
            # Calculate offset
            offset = (page - 1) * limit
            
            # Base queryset
            payments = VendorPayment.objects.filter(user=request.user)
            
            # Apply filters
            if status_filter:
                payments = payments.filter(status=status_filter)
            
            if start_date:
                try:
                    start_date_obj = datetime.strptime(start_date, '%Y-%m-%d')
                    payments = payments.filter(created_at__date__gte=start_date_obj)
                except ValueError:
                    pass
            
            if end_date:
                try:
                    end_date_obj = datetime.strptime(end_date, '%Y-%m-%d')
                    payments = payments.filter(created_at__date__lte=end_date_obj)
                except ValueError:
                    pass
            
            if search:
                payments = payments.filter(
                    Q(recipient_name__icontains=search) |
                    Q(recipient_account__icontains=search) |
                    Q(client_ref_id__icontains=search) |
                    Q(receipt_number__icontains=search)
                )
            
            # Get total count
            total_count = payments.count()
            
            # Apply pagination
            payments = payments.order_by('-created_at')[offset:offset + limit]
            
            # Calculate summary
            summary = payments.aggregate(
                total_amount=Sum('amount'),
                total_fees=Sum('total_fee'),
                total_deductions=Sum('total_deduction'),
                total_count=Count('id')
            )
            
            # Serialize data
            serializer = VendorPaymentResponseSerializer(payments, many=True)
            
            response_data = {
                'status': 0,
                'message': 'Payment history retrieved successfully',
                'data': serializer.data,
                'pagination': {
                    'page': page,
                    'limit': limit,
                    'total': total_count,
                    'pages': (total_count + limit - 1) // limit,
                    'has_next': offset + limit < total_count,
                    'has_prev': page > 1
                },
                'summary': {
                    'total_amount': float(summary['total_amount'] or 0),
                    'total_fees': float(summary['total_fees'] or 0),
                    'total_deductions': float(summary['total_deductions'] or 0),
                    'total_count': summary['total_count']
                }
            }
            
            return Response(response_data)
            
        except Exception as e:
            logger.error(f"❌ Error fetching payment history: {str(e)}")
            return Response({
                'status': 1,
                'message': f'Failed to fetch payment history: {str(e)}'
            }, status=400)
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def payment_details(self, request, pk=None):
        """Get detailed payment information by ID"""
        try:
            payment = get_object_or_404(
                VendorPayment, 
                Q(id=pk) | Q(client_ref_id=pk) | Q(receipt_number=pk),
                user=request.user
            )
            
            serializer = VendorPaymentResponseSerializer(payment)
            
            # Get related transaction
            transaction = Transaction.objects.filter(
                metadata__vendor_payment_id=payment.id
            ).first()
            
            response_data = {
                'status': 0,
                'message': 'Payment details retrieved successfully',
                'data': {
                    **serializer.data,
                    'transaction': {
                        'id': transaction.id if transaction else None,
                        'amount': float(transaction.amount) if transaction else None,
                        'status': transaction.status if transaction else None,
                        'created_at': transaction.created_at if transaction else None
                    } if transaction else None,
                    'wallet_balance': float(request.user.wallet.balance) if hasattr(request.user, 'wallet') else None
                }
            }
            
            return Response(response_data)
            
        except Exception as e:
            logger.error(f"❌ Error fetching payment details: {str(e)}")
            return Response({
                'status': 1,
                'message': f'Failed to fetch payment details: {str(e)}'
            }, status=400)

# Admin/Management Views
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def admin_payment_report(request):
    """
    Admin endpoint to get all vendor payments (requires admin permissions)
    """
    try:
        # Check if user is admin/superuser
        if not request.user.is_staff and not request.user.is_superuser:
            return Response({
                'status': 1,
                'message': 'Permission denied. Admin access required.'
            }, status=403)
        
        # Get query parameters
        user_id = request.query_params.get('user_id', '')
        status_filter = request.query_params.get('status', '')
        start_date = request.query_params.get('start_date', '')
        end_date = request.query_params.get('end_date', '')
        search = request.query_params.get('search', '')
        page = int(request.query_params.get('page', 1))
        limit = int(request.query_params.get('limit', 50))
        
        # Calculate offset
        offset = (page - 1) * limit
        
        # Base queryset
        payments = VendorPayment.objects.select_related('user').all()
        
        # Apply filters
        if user_id:
            payments = payments.filter(user_id=user_id)
        
        if status_filter:
            payments = payments.filter(status=status_filter)
        
        if start_date:
            try:
                start_date_obj = datetime.strptime(start_date, '%Y-%m-%d')
                payments = payments.filter(created_at__date__gte=start_date_obj)
            except ValueError:
                pass
        
        if end_date:
            try:
                end_date_obj = datetime.strptime(end_date, '%Y-%m-%d')
                payments = payments.filter(created_at__date__lte=end_date_obj)
            except ValueError:
                pass
        
        if search:
            payments = payments.filter(
                Q(recipient_name__icontains=search) |
                Q(recipient_account__icontains=search) |
                Q(client_ref_id__icontains=search) |
                Q(receipt_number__icontains=search) |
                Q(user__username__icontains=search) |
                Q(user__phone_number__icontains=search)
            )
        
        # Get total count
        total_count = payments.count()
        
        # Apply pagination
        payments = payments.order_by('-created_at')[offset:offset + limit]
        
        # Prepare data with user info
        payment_data = []
        for payment in payments:
            payment_data.append({
                'id': payment.id,
                'receipt_number': payment.receipt_number,
                'client_ref_id': payment.client_ref_id,
                'user': {
                    'id': payment.user.id,
                    'username': payment.user.username,
                    'phone': payment.user.phone_number,
                    'full_name': payment.user.get_full_name()
                },
                'recipient': {
                    'name': payment.recipient_name,
                    'account': payment.recipient_account[-4:],
                    'ifsc': payment.recipient_ifsc
                },
                'amount': float(payment.amount),
                'total_fee': float(payment.total_fee),
                'total_deduction': float(payment.total_deduction),
                'status': payment.status,
                'status_message': payment.status_message,
                'payment_mode': payment.payment_mode,
                'bank_ref_num': payment.bank_ref_num,
                'utr_number': payment.utr_number,
                'payment_date': payment.payment_date,
                'created_at': payment.created_at,
                'purpose': payment.purpose,
                'remarks': payment.remarks,
                'is_receipt_generated': payment.is_receipt_generated,
                'receipt_generated_at': payment.receipt_generated_at
            })
        
        # Calculate summary statistics
        summary = VendorPayment.objects.aggregate(
            total_amount=Sum('amount'),
            total_fees=Sum('total_fee'),
            total_deductions=Sum('total_deduction'),
            total_count=Count('id'),
            success_count=Count('id', filter=Q(status='success')),
            failed_count=Count('id', filter=Q(status='failed')),
            processing_count=Count('id', filter=Q(status='processing'))
        )
        
        response_data = {
            'status': 0,
            'message': 'Payment report retrieved successfully',
            'data': payment_data,
            'pagination': {
                'page': page,
                'limit': limit,
                'total': total_count,
                'pages': (total_count + limit - 1) // limit,
                'has_next': offset + limit < total_count,
                'has_prev': page > 1
            },
            'summary': {
                'total_amount': float(summary['total_amount'] or 0),
                'total_fees': float(summary['total_fees'] or 0),
                'total_deductions': float(summary['total_deductions'] or 0),
                'total_count': summary['total_count'],
                'success_count': summary['success_count'],
                'failed_count': summary['failed_count'],
                'processing_count': summary['processing_count']
            }
        }
        
        return Response(response_data)
        
    except Exception as e:
        logger.error(f"❌ Error generating admin report: {str(e)}")
        return Response({
            'status': 1,
            'message': f'Failed to generate report: {str(e)}'
        }, status=400)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_payment_summary(request):
    """
    Get payment summary for a specific user or current user
    """
    try:
        user_id = request.query_params.get('user_id', '')
        
        # Check if requesting other user's data (admin only)
        if user_id and str(user_id) != str(request.user.id):
            if not request.user.is_staff and not request.user.is_superuser:
                return Response({
                    'status': 1,
                    'message': 'Permission denied. Admin access required.'
                }, status=403)
            target_user_id = user_id
        else:
            target_user_id = request.user.id
        
        # Get date range
        today = timezone.now().date()
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)
        
        # Calculate statistics
        all_time_stats = VendorPayment.objects.filter(user_id=target_user_id).aggregate(
            total_amount=Sum('amount'),
            total_fees=Sum('total_fee'),
            total_count=Count('id')
        )
        
        monthly_stats = VendorPayment.objects.filter(
            user_id=target_user_id,
            created_at__date__gte=month_ago
        ).aggregate(
            monthly_amount=Sum('amount'),
            monthly_fees=Sum('total_fee'),
            monthly_count=Count('id')
        )
        
        weekly_stats = VendorPayment.objects.filter(
            user_id=target_user_id,
            created_at__date__gte=week_ago
        ).aggregate(
            weekly_amount=Sum('amount'),
            weekly_fees=Sum('total_fee'),
            weekly_count=Count('id')
        )
        
        # Status breakdown
        status_counts = VendorPayment.objects.filter(
            user_id=target_user_id
        ).values('status').annotate(count=Count('id')).order_by('status')
        
        response_data = {
            'status': 0,
            'message': 'Payment summary retrieved successfully',
            'data': {
                'user_id': target_user_id,
                'all_time': {
                    'total_amount': float(all_time_stats['total_amount'] or 0),
                    'total_fees': float(all_time_stats['total_fees'] or 0),
                    'total_count': all_time_stats['total_count']
                },
                'monthly': {
                    'amount': float(monthly_stats['monthly_amount'] or 0),
                    'fees': float(monthly_stats['monthly_fees'] or 0),
                    'count': monthly_stats['monthly_count']
                },
                'weekly': {
                    'amount': float(weekly_stats['weekly_amount'] or 0),
                    'fees': float(weekly_stats['weekly_fees'] or 0),
                    'count': weekly_stats['weekly_count']
                },
                'status_breakdown': [
                    {'status': item['status'], 'count': item['count']}
                    for item in status_counts
                ],
                'last_5_payments': VendorPaymentResponseSerializer(
                    VendorPayment.objects.filter(user_id=target_user_id)
                    .order_by('-created_at')[:5],
                    many=True
                ).data
            }
        }
        
        return Response(response_data)
        
    except Exception as e:
        logger.error(f"❌ Error fetching payment summary: {str(e)}")
        return Response({
            'status': 1,
            'message': f'Failed to fetch payment summary: {str(e)}'
        }, status=400)
        

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def download_vendor_receipt(request, payment_id):
    """
    Download vendor payment receipt as PDF
    Supports both: 
    - payment_id (numeric ID)
    - client_ref_id (VP format)
    """
    try:
        # Try to find by payment_id (numeric ID)
        try:
            payment_id_int = int(payment_id)
            vendor_payment = get_object_or_404(
                VendorPayment, 
                id=payment_id_int, 
                user=request.user
            )
        except ValueError:
            # If not numeric, try to find by client_ref_id
            vendor_payment = get_object_or_404(
                VendorPayment, 
                client_ref_id=payment_id,
                user=request.user
            )
        
        # Check if receipt already generated
        if not vendor_payment.is_receipt_generated:
            vendor_payment.is_receipt_generated = True
            vendor_payment.receipt_generated_at = timezone.now()
            vendor_payment.save()
        
        # Generate receipt data
        receipt_data = vendor_payment.generate_receipt_data()
        
        # Generate PDF
        generator = VendorReceiptGenerator(receipt_data)
        pdf_buffer = generator.generate_pdf()
        
        # Create HTTP response
        filename = f"vendor_receipt_{vendor_payment.receipt_number}.pdf"
        response = HttpResponse(pdf_buffer, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        response['Access-Control-Expose-Headers'] = 'Content-Disposition'
        
        logger.info(f"✅ Receipt downloaded: {filename} for {payment_id}")
        return response
        
    except Exception as e:
        logger.error(f"❌ Receipt download error for {payment_id}: {str(e)}")
        return Response({
            'status': 1,
            'message': f'Failed to generate receipt: {str(e)}'
        }, status=400)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def view_vendor_receipt(request, payment_id):
    """
    View vendor payment receipt in browser
    """
    try:
        # Try to find by payment_id (numeric ID)
        try:
            payment_id_int = int(payment_id)
            vendor_payment = get_object_or_404(
                VendorPayment, 
                id=payment_id_int, 
                user=request.user
            )
        except ValueError:
            # If not numeric, try to find by client_ref_id
            vendor_payment = get_object_or_404(
                VendorPayment, 
                client_ref_id=payment_id,
                user=request.user
            )
        
        # Generate receipt data
        receipt_data = vendor_payment.generate_receipt_data()
        
        # Generate PDF for view
        generator = VendorReceiptGenerator(receipt_data)
        pdf_buffer = generator.generate_pdf()
        
        filename = f"vendor_receipt_{vendor_payment.receipt_number}.pdf"
        response = HttpResponse(pdf_buffer, content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="{filename}"'
        
        return response
        
    except Exception as e:
        logger.error(f"❌ Receipt view error: {str(e)}")
        return Response({
            'status': 1,
            'message': f'Failed to view receipt: {str(e)}'
        }, status=400)
    
    