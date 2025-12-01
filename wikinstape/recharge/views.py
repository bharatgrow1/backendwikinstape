from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.views import APIView
from django.db import transaction
from django.utils import timezone
import logging
from decimal import Decimal

from .models import RechargeTransaction, Operator, Plan, RechargeServiceCharge
from .serializers import (
    RechargeTransactionSerializer, OperatorSerializer, PlanSerializer,
    RechargeRequestSerializer, BillFetchRequestSerializer,
    EKOOperatorResponseSerializer, EKOBillFetchResponseSerializer,
    EKORechargeResponseSerializer
)
from .services.eko_service import recharge_manager

logger = logging.getLogger(__name__)

class RechargeViewSet(viewsets.ViewSet):
    """Recharge API endpoints"""
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['post'])
    def fetch_operators(self, request):
        """
        Fetch operators by category
        POST /api/recharge/fetch_operators/
        {
            "category": "prepaid"  # prepaid, postpaid, dth, electricity, etc.
        }
        """
        category = request.data.get('category', 'prepaid')
        
        result = recharge_manager.get_operators(category)
        
        if result['success']:
            return Response({
                'success': True,
                'category': category,
                'operators': result['operators']
            })
        
        return Response({
            'success': False,
            'message': result['message'],
            'data': result.get('data')
        }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def operator_locations(self, request):
        """
        Fetch operator locations
        GET /api/recharge/operator_locations/
        """
        result = recharge_manager.get_operator_locations()
        
        if result['success']:
            return Response({
                'success': True,
                'locations': result['locations']
            })
        
        return Response({
            'success': False,
            'message': result['message']
        }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def fetch_bill(self, request):
        """
        Fetch bill details (for postpaid/utility)
        POST /api/recharge/fetch_bill/
        {
            "operator_id": "operator_id",
            "mobile_no": "9876543210",
            "utility_acc_no": "consumer_number",  # optional
            "sender_name": "Customer Name"
        }
        """
        serializer = BillFetchRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        data = serializer.validated_data
        result = recharge_manager.fetch_bill_details(
            operator_id=data['operator_id'],
            mobile=data['mobile_no'],
            account_no=data.get('utility_acc_no'),
            sender_name=data.get('sender_name', 'Customer')
        )
        
        response_serializer = EKOBillFetchResponseSerializer(result)
        return Response(response_serializer.data)
    
    @action(detail=False, methods=['post'])
    @transaction.atomic
    def recharge(self, request):
        """
        Perform recharge
        POST /api/recharge/recharge/
        {
            "mobile": "9876543210",
            "amount": 100.00,
            "operator_id": "operator_id",
            "operator_type": "prepaid",
            "circle": "Delhi",
            "consumer_number": "optional",
            "customer_name": "optional",
            "is_plan_recharge": false,
            "plan_id": "optional"
        }
        """
        serializer = RechargeRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        data = serializer.validated_data
        user = request.user
        
        try:
            # Calculate service charge
            service_charge = RechargeServiceCharge.calculate_charge(data['amount'])
            
            # Create transaction record
            recharge_txn = RechargeTransaction.objects.create(
                user=user,
                operator_id=data['operator_id'],
                operator_type=data['operator_type'],
                circle=data.get('circle'),
                mobile_number=data['mobile'],
                consumer_number=data.get('consumer_number'),
                customer_name=data.get('customer_name'),
                amount=data['amount'],
                service_charge=service_charge,
                client_ref_id=f"TXN{int(timezone.now().timestamp())}",
                is_plan_recharge=data.get('is_plan_recharge', False),
                plan_details={
                    'plan_id': data.get('plan_id')
                } if data.get('plan_id') else None,
                status='processing'
            )
            
            # Perform recharge via EKO API
            result = recharge_manager.perform_recharge(
                mobile=data['mobile'],
                amount=data['amount'],
                operator_id=data['operator_id'],
                user=user,
                circle=data.get('circle')
            )
            
            # Update transaction with API response
            recharge_txn.eko_message = result.get('eko_message')
            recharge_txn.eko_txstatus_desc = result.get('txstatus_desc')
            recharge_txn.eko_response_status = result.get('response_status')
            recharge_txn.api_response = result.get('eko_response')
            
            if result['success']:
                recharge_txn.status = 'success'
                recharge_txn.eko_transaction_ref = result.get('eko_transaction_ref')
                recharge_txn.processed_at = timezone.now()
                recharge_txn.completed_at = timezone.now()
                
                # Update transaction ID with EKO's if available
                if result.get('transaction_id'):
                    recharge_txn.transaction_id = result['transaction_id']
                
                message = result.get('message', 'Recharge successful')
            else:
                recharge_txn.status = 'failed'
                recharge_txn.status_message = result.get('message', 'Recharge failed')
                recharge_txn.completed_at = timezone.now()
                message = result.get('message', 'Recharge failed')
            
            recharge_txn.save()
            
            # Process commission if payment is successful
            if result['success'] and recharge_txn.amount > 0:
                try:
                    from commission.views import CommissionManager
                    from users.models import Transaction as WalletTransaction
                    
                    # Find wallet transaction
                    wallet_txn = WalletTransaction.objects.filter(
                        service_submission__isnull=True,
                        description__icontains=f"Recharge {recharge_txn.transaction_id}",
                        status='success'
                    ).first()
                    
                    if wallet_txn:
                        success, comm_message = CommissionManager.process_service_commission(
                            recharge_txn, wallet_txn
                        )
                        if not success:
                            logger.warning(f"Commission processing failed: {comm_message}")
                    
                except ImportError:
                    logger.warning("Commission app not available")
                except Exception as e:
                    logger.error(f"Commission processing error: {str(e)}")
            
            # Serialize response
            txn_serializer = RechargeTransactionSerializer(recharge_txn)
            
            return Response({
                'success': result['success'],
                'message': message,
                'transaction': txn_serializer.data,
                'eko_response': result.get('eko_response', {})
            })
            
        except Exception as e:
            logger.error(f"Recharge error: {str(e)}", exc_info=True)
            return Response({
                'success': False,
                'message': f"Recharge failed: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'])
    def transaction_history(self, request):
        """
        Get user's recharge history
        GET /api/recharge/transaction_history/
        """
        transactions = RechargeTransaction.objects.filter(user=request.user)
        serializer = RechargeTransactionSerializer(transactions, many=True)
        return Response({
            'success': True,
            'count': transactions.count(),
            'transactions': serializer.data
        })
    
    @action(detail=False, methods=['post'])
    def check_status(self, request):
        """
        Check transaction status
        POST /api/recharge/check_status/
        {
            "transaction_id": "RECH123456789"
        }
        """
        transaction_id = request.data.get('transaction_id')
        
        if not transaction_id:
            return Response({
                'success': False,
                'message': 'Transaction ID is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            txn = RechargeTransaction.objects.get(
                transaction_id=transaction_id,
                user=request.user
            )
            
            # If we have EKO transaction ref, check status via API
            if txn.eko_transaction_ref and txn.status in ['processing', 'pending']:
                result = recharge_manager.eko_service.check_status(txn.eko_transaction_ref)
                
                if isinstance(result, dict) and result.get('status') == 'success':
                    # Update transaction status based on API response
                    if result.get('data', {}).get('txstatus_desc', '').lower() == 'success':
                        txn.status = 'success'
                        txn.processed_at = timezone.now()
                        txn.completed_at = timezone.now()
                        txn.save()
            
            serializer = RechargeTransactionSerializer(txn)
            return Response({
                'success': True,
                'transaction': serializer.data
            })
            
        except RechargeTransaction.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Transaction not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Status check error: {str(e)}")
            return Response({
                'success': False,
                'message': f"Failed to check status: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class OperatorViewSet(viewsets.ReadOnlyModelViewSet):
    """Operator management"""
    permission_classes = [IsAuthenticated]
    queryset = Operator.objects.filter(is_active=True)
    serializer_class = OperatorSerializer
    
    @action(detail=False, methods=['get'])
    def by_type(self, request):
        """Get operators by type"""
        operator_type = request.query_params.get('type', 'prepaid')
        operators = self.get_queryset().filter(operator_type=operator_type)
        serializer = self.get_serializer(operators, many=True)
        return Response({
            'success': True,
            'count': operators.count(),
            'operators': serializer.data
        })
    
    @action(detail=False, methods=['get'])
    def with_plans(self, request):
        """Get operators with their plans"""
        operator_type = request.query_params.get('type', 'prepaid')
        operators = self.get_queryset().filter(
            operator_type=operator_type,
            plans__is_active=True
        ).distinct()
        
        result = []
        for operator in operators:
            plans = Plan.objects.filter(
                operator=operator,
                is_active=True
            ).order_by('amount')
            
            operator_data = OperatorSerializer(operator).data
            operator_data['plans'] = PlanSerializer(plans, many=True).data
            result.append(operator_data)
        
        return Response({
            'success': True,
            'operators': result
        })

class PlanViewSet(viewsets.ReadOnlyModelViewSet):
    """Plan management"""
    permission_classes = [IsAuthenticated]
    queryset = Plan.objects.filter(is_active=True)
    serializer_class = PlanSerializer
    
    @action(detail=False, methods=['get'])
    def by_operator(self, request):
        """Get plans by operator"""
        operator_id = request.query_params.get('operator_id')
        plan_type = request.query_params.get('plan_type')
        
        if not operator_id:
            return Response({
                'success': False,
                'message': 'operator_id is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        queryset = self.get_queryset().filter(operator__operator_id=operator_id)
        
        if plan_type:
            queryset = queryset.filter(plan_type=plan_type)
        
        # Sort by amount
        queryset = queryset.order_by('amount')
        
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'success': True,
            'count': queryset.count(),
            'plans': serializer.data
        })
    
    @action(detail=False, methods=['get'])
    def popular_plans(self, request):
        """Get popular plans"""
        operator_id = request.query_params.get('operator_id')
        plan_type = request.query_params.get('plan_type', 'combo')
        
        queryset = self.get_queryset().filter(
            is_popular=True,
            plan_type=plan_type
        )
        
        if operator_id:
            queryset = queryset.filter(operator__operator_id=operator_id)
        
        queryset = queryset.order_by('amount')[:20]  # Limit to 20 popular plans
        
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'success': True,
            'count': queryset.count(),
            'plans': serializer.data
        })