from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import transaction as db_transaction
from django.db.models import Sum, Count, Q, Avg, Max, Min
from django.shortcuts import get_object_or_404
from django.utils import timezone
from datetime import datetime, timedelta
import random
from decimal import InvalidOperation


from .models import *
from .serializers import *
from users.models import User, Wallet, Transaction
from services.models import ServiceSubmission, ServiceSubCategory
from users.permissions import IsAdminUser, IsSuperAdmin
from services.serializers import *


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
    
    def get_serializer_class(self):
        """Use different serializer when role filter is applied"""
        if self.request.query_params.get('role'):
            return RoleFilteredServiceCommissionSerializer
        return ServiceCommissionSerializer
    
    def get_queryset(self):
        """Override get_queryset to add role-based filtering"""
        queryset = super().get_queryset()
        
        # Get role filter from query parameters
        role = self.request.query_params.get('role')
        
        if role:
            # Filter based on the specified role
            if role == 'admin':
                queryset = queryset.filter(admin_commission__gt=0)
            elif role == 'master':
                queryset = queryset.filter(master_commission__gt=0)
            elif role == 'dealer':
                queryset = queryset.filter(dealer_commission__gt=0)
            elif role == 'retailer':
                queryset = queryset.filter(retailer_commission__gt=0)
            elif role == 'superadmin':
                queryset = queryset.annotate(
                    total_distributed=(
                        models.F('admin_commission') + 
                        models.F('master_commission') + 
                        models.F('dealer_commission') + 
                        models.F('retailer_commission')
                    )
                ).filter(total_distributed__lt=100)
        
        return queryset
    
    def get_serializer_context(self):
        """Pass request context to serializer"""
        context = super().get_serializer_context()
        context['request'] = self.request
        return context
    
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
        
        serializer_class = self.get_serializer_class()
        serializer = serializer_class(queryset, many=True, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def distribution_details(self, request, pk=None):
        """Get detailed distribution information for a service commission"""
        service_commission = self.get_object()
        
        distribution_percentages = service_commission.get_distribution_percentages()
        
        return Response({
            'service_commission_id': service_commission.id,
            'service_name': service_commission.service_subcategory.name if service_commission.service_subcategory else service_commission.service_category.name,
            'commission_plan': service_commission.commission_plan.name,
            'commission_type': service_commission.commission_type,
            'commission_value': service_commission.commission_value,
            'distribution_percentages': distribution_percentages,
            'total_distributed': sum([
                service_commission.admin_commission,
                service_commission.master_commission,
                service_commission.dealer_commission,
                service_commission.retailer_commission
            ]),
            'superadmin_share': distribution_percentages['superadmin']
        })

class CommissionTransactionViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = CommissionTransactionSerializer
    
    def get_queryset(self):
        user = self.request.user
        queryset = CommissionTransaction.objects.all()
        
        # Apply role-based filtering
        role = self.request.query_params.get('role')
        if role:
            queryset = queryset.filter(role=role)
        
        # Apply date range filtering
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        if start_date and end_date:
            try:
                start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
                end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
                queryset = queryset.filter(
                    created_at__date__gte=start_date,
                    created_at__date__lte=end_date
                )
            except ValueError:
                pass
        
        if user.is_admin_user():
            return queryset
        
        return queryset.filter(user=user)
    
    @action(detail=False, methods=['get'])
    def my_commissions(self, request):
        """Get current user's commissions with stats"""
        user = request.user
        
        # Get filter parameters
        role = request.query_params.get('role')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        # Base queryset
        commission_qs = CommissionTransaction.objects.filter(
            user=user, 
            status='success',
            transaction_type='credit'
        )
        
        # Apply filters
        if role:
            commission_qs = commission_qs.filter(role=role)
        
        if start_date and end_date:
            try:
                start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
                end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
                commission_qs = commission_qs.filter(
                    created_at__date__gte=start_date,
                    created_at__date__lte=end_date
                )
            except ValueError:
                pass
        
        total_commission = commission_qs.aggregate(total=Sum('commission_amount'))['total'] or 0
        
        # Commission by role breakdown
        commission_by_role = CommissionTransaction.objects.filter(
            user=user,
            status='success',
            transaction_type='credit'
        ).values('role').annotate(
            total=Sum('commission_amount'),
            count=Count('id')
        ).order_by('-total')
        
        # Recent commissions
        recent_commissions = commission_qs.order_by('-created_at')[:10]
        
        # Monthly breakdown for current year
        current_year = timezone.now().year
        monthly_data = CommissionTransaction.objects.filter(
            user=user,
            status='success',
            transaction_type='credit',
            created_at__year=current_year
        ).extra({'month': "EXTRACT(month FROM created_at)"}).values('month').annotate(
            total=Sum('commission_amount')
        ).order_by('month')
        
        serializer = self.get_serializer(recent_commissions, many=True)
        
        return Response({
            'total_commission': total_commission,
            'commission_by_role': list(commission_by_role),
            'recent_commissions': serializer.data,
            'monthly_breakdown': list(monthly_data),
            'filters_applied': {
                'role': role,
                'start_date': start_date,
                'end_date': end_date
            }
        })
    
    @action(detail=False, methods=['get'])
    def role_stats(self, request):
        """Get commission statistics by role for current user"""
        user = request.user
        
        role_stats = CommissionTransaction.objects.filter(
            user=user,
            status='success',
            transaction_type='credit'
        ).values('role').annotate(
            total_commission=Sum('commission_amount'),
            transaction_count=Count('id'),
            avg_commission=Avg('commission_amount')
        ).order_by('-total_commission')
        
        return Response({
            'role_stats': list(role_stats),
            'user_role': user.role
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
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by user role if provided
        user_role = self.request.query_params.get('user_role')
        if user_role:
            queryset = queryset.filter(user__role=user_role)
        
        # Filter by status if provided
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        return queryset
    
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
            
            distribution_percentages = commission_config.get_distribution_percentages()
            
            return Response({
                'transaction_amount': transaction_amount,
                'service': service_subcategory.name,
                'commission_plan': commission_plan.name,
                'total_commission': commission_config.calculate_commission(transaction_amount),
                'distribution_amounts': distribution,
                'distribution_percentages': distribution_percentages,
                'hierarchy_users': {
                    role: {
                        'username': user.username if user else 'N/A',
                        'user_id': user.id if user else None,
                        'role': role
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
        """Get commission statistics overview with role-based filtering"""
        
        # Get filter parameters
        role = request.query_params.get('role')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        # Base queryset
        commission_qs = CommissionTransaction.objects.filter(
            status='success', 
            transaction_type='credit'
        )
        
        # Apply filters
        if role:
            commission_qs = commission_qs.filter(role=role)
        
        if start_date and end_date:
            try:
                start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
                end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
                commission_qs = commission_qs.filter(
                    created_at__date__gte=start_date,
                    created_at__date__lte=end_date
                )
            except ValueError:
                pass
        
        total_commission = commission_qs.aggregate(total=Sum('commission_amount'))['total'] or 0
        
        pending_payouts = CommissionPayout.objects.filter(
            status='pending'
        ).aggregate(total=Sum('total_amount'))['total'] or 0
        
        total_payouts = CommissionPayout.objects.filter(
            status='completed'
        ).aggregate(total=Sum('total_amount'))['total'] or 0
        
        commission_by_role = commission_qs.values('role').annotate(
            total=Sum('commission_amount'),
            count=Count('id')
        ).order_by('-total')
        
        top_services = commission_qs.values(
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
            'top_services': list(top_services),
            'filters_applied': {
                'role': role,
                'start_date': start_date,
                'end_date': end_date
            }
        })
    
    @action(detail=False, methods=['get'])
    def role_performance(self, request):
        """Get detailed performance statistics by role"""
        
        role_stats = CommissionTransaction.objects.filter(
            status='success',
            transaction_type='credit'
        ).values('role').annotate(
            total_commission=Sum('commission_amount'),
            transaction_count=Count('id'),
            avg_commission=Avg('commission_amount'),
            max_commission=Max('commission_amount'),
            min_commission=Min('commission_amount')
        ).order_by('-total_commission')
        
        # User count by role
        user_count_by_role = User.objects.filter(
            is_active=True
        ).exclude(role__in=['superadmin']).values('role').annotate(
            user_count=Count('id')
        )
        
        return Response({
            'role_performance': list(role_stats),
            'user_distribution': list(user_count_by_role)
        })

class CommissionManager:
    @staticmethod
    def process_service_commission(service_submission, main_transaction):
        """Process commission for a service submission including superadmin"""
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
        


class DealerRetailerCommissionViewSet(viewsets.ReadOnlyModelViewSet):
    """View for dealers and retailers to see their commission rates"""
    permission_classes = [IsAuthenticated]
    serializer_class = DealerRetailerServiceCommissionSerializer
    
    def get_queryset(self):
        """Only show services where the user's role gets commission with filtering"""
        user = self.request.user
        user_role = user.role
        
        # Only allow dealer and retailer roles
        if user_role not in ['dealer', 'retailer']:
            return ServiceCommission.objects.none()
        
        queryset = ServiceCommission.objects.filter(is_active=True)
        
        # Filter based on user's role
        if user_role == 'dealer':
            queryset = queryset.filter(dealer_commission__gt=0)
        elif user_role == 'retailer':
            queryset = queryset.filter(retailer_commission__gt=0)
        
        # Apply category and subcategory filtering
        service_category_id = self.request.query_params.get('service_category')
        if service_category_id:
            queryset = queryset.filter(service_category_id=service_category_id)
        
        service_subcategory_id = self.request.query_params.get('service_subcategory')
        if service_subcategory_id:
            queryset = queryset.filter(service_subcategory_id=service_subcategory_id)
        
        # Apply commission plan filtering if needed
        commission_plan_id = self.request.query_params.get('commission_plan')
        if commission_plan_id:
            queryset = queryset.filter(commission_plan_id=commission_plan_id)
        
        return queryset
    
    def get_serializer_context(self):
        """Pass request context to serializer"""
        context = super().get_serializer_context()
        context['request'] = self.request
        return context
    
    @action(detail=False, methods=['get'])
    def my_commission_summary(self, request):
        """Get summary of commission rates for current user with filtering"""
        user = request.user
        user_role = user.role
        
        if user_role not in ['dealer', 'retailer']:
            return Response(
                {'error': 'This endpoint is only for dealers and retailers'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        queryset = self.get_queryset()
        
        # Get filter counts
        total_services = queryset.count()
        
        # Get unique categories and subcategories for the filtered results
        categories = ServiceCategory.objects.filter(
            id__in=queryset.values_list('service_category_id', flat=True).distinct()
        )
        
        subcategories = ServiceSubCategory.objects.filter(
            id__in=queryset.values_list('service_subcategory_id', flat=True).distinct()
        )
        
        summary_data = []
        for commission in queryset:
            distribution_percentages = commission.get_distribution_percentages()
            user_percentage = distribution_percentages.get(user_role, 0)
            
            service_data = {
                'service_id': commission.service_subcategory.id if commission.service_subcategory else commission.service_category.id,
                'service_name': commission.service_subcategory.name if commission.service_subcategory else commission.service_category.name,
                'service_category': commission.service_category.name if commission.service_category else 'N/A',
                'service_category_id': commission.service_category.id if commission.service_category else None,
                'service_subcategory_id': commission.service_subcategory.id if commission.service_subcategory else None,
                'total_commission_rate': commission.commission_value,
                'commission_type': commission.commission_type,
                'your_commission_percentage': user_percentage,
                'commission_plan': commission.commission_plan.name,
                'is_active': commission.is_active
            }
            summary_data.append(service_data)
        
        return Response({
            'user': {
                'id': user.id,
                'username': user.username,
                'role': user_role
            },
            'total_services': total_services,
            'available_categories': ServiceCategorySerializer(categories, many=True).data,
            'available_subcategories': ServiceSubCategorySerializer(subcategories, many=True).data,
            'commission_rates': summary_data,
            'filters_applied': {
                'service_category': request.query_params.get('service_category'),
                'service_subcategory': request.query_params.get('service_subcategory'),
                'commission_plan': request.query_params.get('commission_plan')
            }
        })