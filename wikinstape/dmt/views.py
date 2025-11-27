from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import transaction as db_transaction
from django.shortcuts import get_object_or_404
import logging

from dmt.models import (DMTTransaction, DMTRecipient, DMTSenderProfile, 
                    DMTServiceCharge, DMTBank)
from dmt.serializers import (DMTTransactionSerializer, DMTRecipientSerializer,
                         DMTRecipientCreateSerializer, DMTSenderProfileSerializer,
                         DMTTransactionCreateSerializer, DMTOTPVerifySerializer,
                         DMTBiometricKycSerializer, DMTKycOTPVerifySerializer,
                         DMTLimitSerializer, DMTServiceChargeSerializer,
                         DMTBankSerializer)
from dmt.services.dmt_manager import dmt_manager

logger = logging.getLogger(__name__)

class DMTViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def dashboard(self, request):
        """Get DMT dashboard data"""
        user = request.user
        
        try:
            # Get sender profile
            sender_profile = DMTSenderProfile.objects.get(user=user)
            profile_serializer = DMTSenderProfileSerializer(sender_profile)
            
            # Get recent transactions
            recent_transactions = DMTTransaction.objects.filter(
                user=user
            ).order_by('-initiated_at')[:5]
            transaction_serializer = DMTTransactionSerializer(recent_transactions, many=True)
            
            # Get recipients count
            recipients_count = DMTRecipient.objects.filter(user=user, is_active=True).count()
            
            # Get limits
            limits_data = {
                'daily_limit': sender_profile.daily_limit,
                'monthly_limit': sender_profile.monthly_limit,
                'per_transaction_limit': sender_profile.per_transaction_limit,
                'daily_usage': sender_profile.daily_usage,
                'monthly_usage': sender_profile.monthly_usage,
                'available_daily': sender_profile.daily_limit - sender_profile.daily_usage,
                'available_monthly': sender_profile.monthly_limit - sender_profile.monthly_usage,
            }
            limits_serializer = DMTLimitSerializer(limits_data)
            
            return Response({
                'sender_profile': profile_serializer.data,
                'recent_transactions': transaction_serializer.data,
                'recipients_count': recipients_count,
                'limits': limits_serializer.data
            })
            
        except DMTSenderProfile.DoesNotExist:
            return Response({
                'sender_profile': None,
                'recent_transactions': [],
                'recipients_count': 0,
                'limits': None,
                'message': 'Please complete KYC to use DMT services'
            })

class DMTKYCViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def check_sender_profile(self, request):
        """Check sender profile in EKO system"""
        mobile = request.query_params.get('mobile')
        
        if not mobile:
            return Response(
                {'error': 'Mobile number is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        success, message, profile_data = dmt_manager.get_sender_profile(mobile)
        
        if success:
            return Response({
                'success': True,
                'message': message,
                'profile_data': profile_data,
                'kyc_required': False
            })
        else:
            return Response({
                'success': False,
                'message': message,
                'kyc_required': True
            })
    
    @action(detail=False, methods=['post'])
    def biometric_kyc(self, request):
        """Perform biometric KYC"""
        serializer = DMTBiometricKycSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        mobile = request.data.get('mobile', request.user.phone_number)
        if not mobile:
            return Response(
                {'error': 'Mobile number is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        success, message, sender_profile = dmt_manager.register_sender_biometric_kyc(
            request.user,
            mobile,
            serializer.validated_data['aadhar_number'],
            serializer.validated_data['piddata']
        )
        
        if success:
            profile_serializer = DMTSenderProfileSerializer(sender_profile)
            return Response({
                'success': True,
                'message': message,
                'sender_profile': profile_serializer.data
            })
        else:
            return Response({
                'success': False,
                'error': message
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def verify_kyc_otp(self, request):
        """Verify KYC OTP"""
        serializer = DMTKycOTPVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        mobile = request.data.get('mobile', request.user.phone_number)
        if not mobile:
            return Response(
                {'error': 'Mobile number is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        success, message, kyc_data = dmt_manager.verify_sender_kyc_otp(
            mobile,
            serializer.validated_data['otp'],
            serializer.validated_data['otp_ref_id'],
            serializer.validated_data['kyc_request_id']
        )
        
        if success:
            # Update sender profile
            sender_profile, created = DMTSenderProfile.objects.get_or_create(
                user=request.user,
                defaults={'mobile': mobile}
            )
            sender_profile.kyc_status = 'verified'
            sender_profile.kyc_method = 'otp'
            sender_profile.kyc_verified_at = timezone.now()
            sender_profile.eko_customer_id = mobile
            sender_profile.eko_profile_data = kyc_data
            sender_profile.save()
            
            profile_serializer = DMTSenderProfileSerializer(sender_profile)
            return Response({
                'success': True,
                'message': message,
                'sender_profile': profile_serializer.data
            })
        else:
            return Response({
                'success': False,
                'error': message
            }, status=status.HTTP_400_BAD_REQUEST)

class DMTRecipientViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = DMTRecipientSerializer
    
    def get_queryset(self):
        return DMTRecipient.objects.filter(user=self.request.user, is_active=True)
    
    def get_serializer_class(self):
        if self.action == 'create':
            return DMTRecipientCreateSerializer
        return DMTRecipientSerializer
    
    def perform_create(self, serializer):
        """Create recipient via EKO API"""
        recipient_data = serializer.validated_data
        
        success, message, recipient = dmt_manager.add_recipient(
            self.request.user, 
            recipient_data
        )
        
        if not success:
            from rest_framework.exceptions import ValidationError
            raise ValidationError({'non_field_errors': [message]})
    
    @action(detail=False, methods=['get'])
    def banks(self, request):
        """Get available banks"""
        banks = DMTBank.objects.filter(is_active=True)
        serializer = DMTBankSerializer(banks, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def verify(self, request, pk=None):
        """Verify recipient"""
        recipient = self.get_object()
        
        # In a real scenario, you might want to re-verify with EKO
        # For now, we'll just return the current status
        serializer = self.get_serializer(recipient)
        return Response({
            'success': True,
            'message': 'Recipient verification status',
            'recipient': serializer.data
        })

class DMTTransactionViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = DMTTransactionSerializer
    
    def get_queryset(self):
        return DMTTransaction.objects.filter(user=self.request.user)
    
    @action(detail=False, methods=['post'])
    def initiate(self, request):
        """Initiate DMT transaction"""
        serializer = DMTTransactionCreateSerializer(
            data=request.data, 
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        
        success, message, dmt_transaction = dmt_manager.initiate_transaction(
            request.user,
            serializer.validated_data
        )
        
        if success:
            transaction_serializer = DMTTransactionSerializer(dmt_transaction)
            return Response({
                'success': True,
                'message': message,
                'transaction': transaction_serializer.data
            })
        else:
            return Response({
                'success': False,
                'error': message
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def verify_otp(self, request):
        """Verify OTP and process transaction"""
        serializer = DMTOTPVerifySerializer(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        
        success, message, dmt_transaction = dmt_manager.verify_and_process_transaction(
            request.user,
            serializer.validated_data
        )
        
        if success:
            transaction_serializer = DMTTransactionSerializer(dmt_transaction)
            return Response({
                'success': True,
                'message': message,
                'transaction': transaction_serializer.data
            })
        else:
            return Response({
                'success': False,
                'error': message
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def service_charges(self, request):
        """Get service charges"""
        charges = DMTServiceCharge.objects.filter(is_active=True)
        serializer = DMTServiceChargeSerializer(charges, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def calculate_charge(self, request):
        """Calculate service charge for amount"""
        amount = request.query_params.get('amount')
        
        if not amount:
            return Response(
                {'error': 'Amount parameter is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            amount = float(amount)
            service_charge = DMTServiceCharge.calculate_charge(amount)
            
            return Response({
                'amount': amount,
                'service_charge': service_charge,
                'total_amount': amount + service_charge
            })
        except ValueError:
            return Response(
                {'error': 'Invalid amount'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['get'])
    def status(self, request, pk=None):
        """Get transaction status"""
        transaction = self.get_object()
        serializer = DMTTransactionSerializer(transaction)
        return Response(serializer.data)

class DMTLimitViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def my_limits(self, request):
        """Get current user's DMT limits"""
        try:
            sender_profile = DMTSenderProfile.objects.get(user=request.user)
            limits_data = {
                'daily_limit': sender_profile.daily_limit,
                'monthly_limit': sender_profile.monthly_limit,
                'per_transaction_limit': sender_profile.per_transaction_limit,
                'daily_usage': sender_profile.daily_usage,
                'monthly_usage': sender_profile.monthly_usage,
                'available_daily': sender_profile.daily_limit - sender_profile.daily_usage,
                'available_monthly': sender_profile.monthly_limit - sender_profile.monthly_usage,
            }
            serializer = DMTLimitSerializer(limits_data)
            return Response(serializer.data)
        except DMTSenderProfile.DoesNotExist:
            return Response(
                {'error': 'Sender profile not found. Please complete KYC.'},
                status=status.HTTP_404_NOT_FOUND
            )

# Admin Views
class DMTAdminViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    
    def get_permissions(self):
        """Only allow admin users"""
        from users.permissions import IsAdminUser
        return [IsAuthenticated(), IsAdminUser()]
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get DMT statistics for admin"""
        total_transactions = DMTTransaction.objects.count()
        successful_transactions = DMTTransaction.objects.filter(status='success').count()
        total_amount = DMTTransaction.objects.filter(status='success').aggregate(
            total=models.Sum('amount')
        )['total'] or 0
        total_service_charge = DMTTransaction.objects.filter(status='success').aggregate(
            total=models.Sum('service_charge')
        )['total'] or 0
        
        recent_transactions = DMTTransaction.objects.select_related('user', 'recipient').order_by('-initiated_at')[:10]
        transaction_serializer = DMTTransactionSerializer(recent_transactions, many=True)
        
        return Response({
            'total_transactions': total_transactions,
            'successful_transactions': successful_transactions,
            'success_rate': (successful_transactions / total_transactions * 100) if total_transactions > 0 else 0,
            'total_amount': total_amount,
            'total_service_charge': total_service_charge,
            'recent_transactions': transaction_serializer.data
        })