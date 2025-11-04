from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import transaction as db_transaction
from django.db.models import Sum, Count, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from datetime import datetime, timedelta
import random

from .models import *
from .serializers import *
from users.models import User, Wallet, Transaction
from services.models import ServiceSubmission, ServiceSubCategory
from users.permissions import IsAdminUser, IsSuperAdmin

class CommissionPlanViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsAdminUser]
    queryset = CommissionPlan.objects.all()
    serializer_class = CommissionPlanSerializer
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

class ServiceCommissionViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsAdminUser]
    queryset = ServiceCommission.objects.all()
    serializer_class = ServiceCommissionSerializer
    filter_fields = ['service_category', 'service_subcategory', 'commission_plan', 'is_active']
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
    
    @action(detail=False, methods=['get'])
    def by_service(self, request):
        """Get commissions for specific service"""
        subcategory_id = request.query_params.get('subcategory_id')
        category_id = request.query_params.get('category_id')
        
        if not subcategory_id and not category_id:
            return Response(
                {'error': 'Either subcategory_id or category_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        queryset = self.get_queryset()
        if subcategory_id:
            queryset = queryset.filter(service_subcategory_id=subcategory_id)
        elif category_id:
            queryset = queryset.filter(service_category_id=category_id)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

class CommissionTransactionViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = CommissionTransactionSerializer
    
    def get_queryset(self):
        user = self.request.user
        
        if user.is_admin_user():
            return CommissionTransaction.objects.all()
        
        return CommissionTransaction.objects.filter(user=user)
    
    @action(detail=False, methods=['get'])
    def my_commissions(self, request):
        """Get current user's commissions with stats"""
        user = request.user
        
        total_commission = CommissionTransaction.objects.filter(
            user=user, 
            status='success',
            transaction_type='credit'
        ).aggregate(total=Sum('commission_amount'))['total'] or 0
        
        recent_commissions = self.get_queryset().filter(user=user)[:10]
        
        monthly_data = CommissionTransaction.objects.filter(
            user=user,
            status='success',
            transaction_type='credit',
            created_at__gte=timezone.now() - timedelta(days=30)
        ).extra({'month': "date_trunc('month', created_at)"}).values('month').annotate(
            total=Sum('commission_amount')
        ).order_by('-month')
        
        serializer = self.get_serializer(recent_commissions, many=True)
        
        return Response({
            'total_commission': total_commission,
            'recent_commissions': serializer.data,
            'monthly_breakdown': monthly_data
        })

class UserCommissionPlanViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsAdminUser]
    queryset = UserCommissionPlan.objects.all()
    serializer_class = UserCommissionPlanSerializer
    
    def perform_create(self, serializer):
        serializer.save(assigned_by=self.request.user)
    
    @action(detail=False, methods=['post'])
    def assign_plan(self, request):
        """Assign commission plan to multiple users"""
        serializer = AssignCommissionPlanSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user_ids = serializer.validated_data['user_ids']
        commission_plan_id = serializer.validated_data['commission_plan_id']
        
        try:
            commission_plan = CommissionPlan.objects.get(id=commission_plan_id)
        except CommissionPlan.DoesNotExist:
            return Response(
                {'error': 'Commission plan not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        assigned_count = 0
        for user_id in user_ids:
            try:
                user = User.objects.get(id=user_id)
                UserCommissionPlan.objects.update_or_create(
                    user=user,
                    defaults={
                        'commission_plan': commission_plan,
                        'assigned_by': request.user,
                        'is_active': True
                    }
                )
                assigned_count += 1
            except User.DoesNotExist:
                continue
        
        return Response({
            'message': f'Commission plan assigned to {assigned_count} users',
            'assigned_count': assigned_count
        })
    
    @action(detail=False, methods=['get'])
    def user_plan(self, request):
        """Get current user's commission plan"""
        try:
            user_plan = UserCommissionPlan.objects.get(user=request.user, is_active=True)
            serializer = self.get_serializer(user_plan)
            return Response(serializer.data)
        except UserCommissionPlan.DoesNotExist:
            return Response({
                'message': 'No active commission plan assigned',
                'has_plan': False
            })

class CommissionPayoutViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsAdminUser]
    queryset = CommissionPayout.objects.all()
    serializer_class = CommissionPayoutSerializer
    
    @action(detail=True, methods=['post'])
    def process_payout(self, request, pk=None):
        """Process commission payout"""
        payout = self.get_object()
        
        if payout.status != 'pending':
            return Response(
                {'error': 'Payout already processed'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            with db_transaction.atomic():
                wallet = payout.user.wallet
                wallet.balance += payout.total_amount
                wallet.save()
                
                Transaction.objects.create(
                    wallet=wallet,
                    amount=payout.total_amount,
                    transaction_type='credit',
                    transaction_category='commission',
                    description=f"Commission payout {payout.reference_number}",
                    created_by=request.user
                )
                
                payout.status = 'completed'
                payout.processed_by = request.user
                payout.processed_at = timezone.now()
                payout.save()
                
                return Response({
                    'message': 'Payout processed successfully',
                    'payout': CommissionPayoutSerializer(payout).data
                })
                
        except Exception as e:
            return Response(
                {'error': f'Payout processing failed: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class CommissionCalculatorView(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['post'])
    def calculate(self, request):
        """Calculate commission for a transaction"""
        serializer = CommissionCalculatorSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        service_subcategory_id = serializer.validated_data['service_subcategory_id']
        transaction_amount = serializer.validated_data['transaction_amount']
        user_id = serializer.validated_data.get('user_id', request.user.id)
        
        try:
            user = User.objects.get(id=user_id)
            service_subcategory = ServiceSubCategory.objects.get(id=service_subcategory_id)
            
            try:
                user_plan = UserCommissionPlan.objects.get(user=user, is_active=True)
                commission_plan = user_plan.commission_plan
            except UserCommissionPlan.DoesNotExist:
                return Response(
                    {'error': 'No active commission plan assigned to user'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            commission_config = ServiceCommission.objects.get(
                service_subcategory=service_subcategory,
                commission_plan=commission_plan,
                is_active=True
            )
            
            distribution, hierarchy_users = commission_config.distribute_commission(
                transaction_amount, user
            )
            
            return Response({
                'transaction_amount': transaction_amount,
                'service': service_subcategory.name,
                'commission_plan': commission_plan.name,
                'total_commission': commission_config.calculate_commission(transaction_amount),
                'distribution': distribution,
                'hierarchy_users': {
                    role: {
                        'username': user.username if user else 'N/A',
                        'user_id': user.id if user else None
                    } for role, user in hierarchy_users.items()
                }
            })
            
        except (User.DoesNotExist, ServiceSubCategory.DoesNotExist, ServiceCommission.DoesNotExist) as e:
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_404_NOT_FOUND
            )

class CommissionStatsViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated, IsAdminUser]
    
    @action(detail=False, methods=['get'])
    def overview(self, request):
        """Get commission statistics overview"""
        total_commission = CommissionTransaction.objects.filter(
            status='success', 
            transaction_type='credit'
        ).aggregate(total=Sum('commission_amount'))['total'] or 0
        
        pending_payouts = CommissionPayout.objects.filter(
            status='pending'
        ).aggregate(total=Sum('total_amount'))['total'] or 0
        
        total_payouts = CommissionPayout.objects.filter(
            status='completed'
        ).aggregate(total=Sum('total_amount'))['total'] or 0
        
        commission_by_role = CommissionTransaction.objects.filter(
            status='success', 
            transaction_type='credit'
        ).values('role').annotate(
            total=Sum('commission_amount')
        ).order_by('-total')
        
        top_services = CommissionTransaction.objects.filter(
            status='success', 
            transaction_type='credit'
        ).values(
            'service_submission__service_form__name'
        ).annotate(
            total=Sum('commission_amount'),
            count=Count('id')
        ).order_by('-total')[:10]
        
        return Response({
            'total_commission': total_commission,
            'pending_payouts': pending_payouts,
            'total_payouts': total_payouts,
            'commission_by_role': list(commission_by_role),
            'top_services': list(top_services)
        })

class CommissionManager:
    @staticmethod
    def process_service_commission(service_submission, main_transaction):
        """Process commission for a service submission"""
        try:
            with db_transaction.atomic():
                retailer_user = service_submission.submitted_by
                transaction_amount = service_submission.amount
                
                if not retailer_user:
                    return False, "No retailer user found for this submission"
                
                try:
                    user_plan = UserCommissionPlan.objects.get(user=retailer_user, is_active=True)
                    commission_plan = user_plan.commission_plan
                except UserCommissionPlan.DoesNotExist:
                    return False, "No active commission plan for user"
                
                try:
                    commission_config = ServiceCommission.objects.get(
                        service_subcategory=service_submission.service_subcategory,
                        commission_plan=commission_plan,
                        is_active=True
                    )
                except ServiceCommission.DoesNotExist:
                    try:
                        commission_config = ServiceCommission.objects.get(
                            service_category=service_submission.service_subcategory.category,
                            commission_plan=commission_plan,
                            is_active=True
                        )
                    except ServiceCommission.DoesNotExist:
                        return False, "No commission configuration found for this service"
                
                distribution, hierarchy_users = commission_config.distribute_commission(
                    transaction_amount, retailer_user
                )
                
                for role, amount in distribution.items():
                    if amount > 0 and hierarchy_users[role]:
                        CommissionTransaction.objects.create(
                            main_transaction=main_transaction,
                            service_submission=service_submission,
                            commission_config=commission_config,
                            commission_plan=commission_plan,
                            user=hierarchy_users[role],
                            role=role,
                            commission_amount=amount,
                            transaction_type='credit',
                            status='success',
                            description=f"Commission for {service_submission.service_form.name}",
                            retailer_user=retailer_user,
                            original_transaction_amount=transaction_amount
                        )
                        
                        wallet = hierarchy_users[role].wallet
                        wallet.balance += amount
                        wallet.save()
                        
                        Transaction.objects.create(
                            wallet=wallet,
                            amount=amount,
                            net_amount=amount,
                            service_charge=0,
                            transaction_type='credit',
                            transaction_category='commission',
                            description=f"Commission from {service_submission.service_form.name}",
                            created_by=hierarchy_users[role],
                            status='success'
                        )
                
                return True, "Commission processed and distributed successfully"
                
        except Exception as e:
            return False, f"Commission processing failed: {str(e)}"