from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from django.contrib.auth.models import Permission
from django.db import transaction as db_transaction
from django.shortcuts import get_object_or_404
from django.contrib.contenttypes.models import ContentType
from django.apps import apps

from .models import User, EmailOTP, Wallet, Transaction, BalanceRequest, RolePermission, ForgotPasswordOTP
from .permissions import IsSuperAdmin, IsAdminUser, IsMasterUser, HasPermission, ModelViewPermission
from .serializers import (
    LoginSerializer, OTPVerifySerializer, UserSerializer, WalletSerializer, 
    TransactionSerializer, BalanceRequestCreateSerializer, BalanceRequestUpdateSerializer,
    PermissionSerializer, UserPermissionSerializer, UserPermissionsSerializer,
    ForgotPasswordSerializer, GrantRolePermissionSerializer, VerifyForgotPasswordOTPSerializer, 
    ResetPasswordSerializer, RolePermissionSerializer, UserCreateSerializer
)
from .utils import send_otp_email

class PermissionViewSet(viewsets.ViewSet):
    """Manage permissions - Super Admin and Master only"""
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.action in ['all_permissions', 'model_permissions', 'user_permissions', 'role_permissions']:
            return [IsAdminUser()]
        return [IsSuperAdmin()]

    def list(self, request):
        """Default list view"""
        return Response({
            "message": "Permission management endpoints",
            "available_actions": [
                "all_permissions",
                "model_permissions", 
                "assign_user_permissions",
                "user_permissions",
                "available_models",
                "grant_role_permissions",
                "role_permissions"
            ]
        })
        

    @action(detail=False, methods=['get'])
    def all_permissions(self, request):
        """Get all available permissions in system"""
        permissions = Permission.objects.all().select_related('content_type')
        serializer = PermissionSerializer(permissions, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def model_permissions(self, request):
        """Get permissions for specific model"""
        model_name = request.query_params.get('model')
        app_label = request.query_params.get('app_label')
        
        if not model_name or not app_label:
            return Response(
                {'error': 'Both model and app_label parameters are required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            content_type = ContentType.objects.get(app_label=app_label, model=model_name)
            permissions = Permission.objects.filter(content_type=content_type)
            serializer = PermissionSerializer(permissions, many=True)
            return Response(serializer.data)
        except ContentType.DoesNotExist:
            return Response(
                {'error': 'Model not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=False, methods=['post'])
    def assign_user_permissions(self, request):
        """Assign permissions to specific user"""
        serializer = UserPermissionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user_id = serializer.validated_data['user_id']
        permission_ids = serializer.validated_data['permission_ids']
        
        try:
            user = User.objects.get(id=user_id)
            permissions = Permission.objects.filter(id__in=permission_ids)
            
            # Clear existing permissions and assign new ones
            user.user_permissions.clear()
            user.user_permissions.add(*permissions)
            
            return Response({
                'message': f'Assigned {permissions.count()} permissions to {user.username}',
                'user': UserPermissionsSerializer(user).data
            })
            
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=False, methods=['get'])
    def user_permissions(self, request):
        """Get permissions for specific user"""
        user_id = request.query_params.get('user_id')
        if not user_id:
            return Response(
                {'error': 'user_id parameter is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            user = User.objects.get(id=user_id)
            serializer = UserPermissionsSerializer(user)
            return Response(serializer.data)
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=False, methods=['get'])
    def available_models(self, request):
        """Get all available models in the system"""
        models_list = []
        for app_config in apps.get_app_configs():
            for model in app_config.get_models():
                # Skip Django internal models
                if app_config.label in ['auth', 'contenttypes', 'sessions', 'admin']:
                    continue
                    
                content_type = ContentType.objects.get_for_model(model)
                permissions = Permission.objects.filter(content_type=content_type)
                
                models_list.append({
                    'app_label': app_config.label,
                    'model_name': model._meta.model_name,
                    'verbose_name': model._meta.verbose_name,
                    'verbose_name_plural': model._meta.verbose_name_plural,
                    'content_type_id': content_type.id,
                    'permissions_count': permissions.count()
                })
        
        return Response(models_list)

    @action(detail=False, methods=['post'])
    def grant_role_permissions(self, request):
        """Grant permissions to a role"""
        serializer = GrantRolePermissionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        role = serializer.validated_data['role']
        permission_ids = serializer.validated_data['permission_ids']
        
        permissions = Permission.objects.filter(id__in=permission_ids)
        granted_count = 0
        
        for permission in permissions:
            role_perm, created = RolePermission.objects.get_or_create(
                role=role,
                permission=permission,
                defaults={'granted_by': request.user}
            )
            if created:
                granted_count += 1
        
        return Response({
            'message': f'Granted {granted_count} permissions to {role} role',
            'role': role,
            'granted_permissions': PermissionSerializer(permissions, many=True).data
        })

    @action(detail=False, methods=['get'])
    def role_permissions(self, request):
        """Get all permissions for a specific role"""
        role = request.query_params.get('role')
        if not role:
            return Response(
                {'error': 'role parameter is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        role_permissions = RolePermission.objects.filter(role=role).select_related('permission')
        serializer = RolePermissionSerializer(role_permissions, many=True)
        
        return Response({
            'role': role,
            'permissions': serializer.data
        })

class AuthViewSet(viewsets.ViewSet):
    """Handles login with password + OTP verification"""

    @action(detail=False, methods=['post'])
    def login(self, request):
        """Step 1: Verify username/password and send OTP"""
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        username = serializer.validated_data['username']
        password = serializer.validated_data['password']

        user = authenticate(username=username, password=password)
        if not user:
            return Response({'error': 'Invalid credentials'}, status=status.HTTP_400_BAD_REQUEST)

        otp_obj, _ = EmailOTP.objects.get_or_create(user=user)
        otp = otp_obj.generate_otp()
        send_otp_email(user.email, otp, is_password_reset=False)

        return Response({'message': 'OTP sent to your email'}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'])
    def verify_otp(self, request):
        """Step 2: Verify OTP and return JWT tokens"""
        serializer = OTPVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        username = serializer.validated_data['username']
        otp = serializer.validated_data['otp']

        try:
            user = User.objects.get(username=username)
            otp_obj = EmailOTP.objects.get(user=user, otp=otp)
        except (User.DoesNotExist, EmailOTP.DoesNotExist):
            return Response({'error': 'Invalid OTP or username'}, status=status.HTTP_400_BAD_REQUEST)

        if otp_obj.is_expired():
            return Response({'error': 'OTP expired'}, status=status.HTTP_400_BAD_REQUEST)

        otp_obj.delete()

        refresh = RefreshToken.for_user(user)
        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'role': user.role,
            'user_id': user.id,
            'username': user.username,
            'permissions': list(user.get_all_permissions())
        }, status=status.HTTP_200_OK)
    


    @action(detail=False, methods=['post'])
    def forgot_password(self, request):
        """Step 1: Request OTP for password reset"""
        serializer = ForgotPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        username = serializer.validated_data['username']

        try:
            user = User.objects.get(username=username)
            otp_obj, _ = ForgotPasswordOTP.objects.get_or_create(user=user)
            otp = otp_obj.generate_otp()
            
            # Send OTP via email
            send_otp_email(user.email, otp, is_password_reset=True)

            return Response({
                'message': 'OTP sent to your email for password reset',
                'username': username
            }, status=status.HTTP_200_OK)

        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=False, methods=['post'])
    def verify_forgot_password_otp(self, request):
        """Step 2: Verify OTP for password reset"""
        serializer = VerifyForgotPasswordOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        username = serializer.validated_data['username']
        otp = serializer.validated_data['otp']

        try:
            user = User.objects.get(username=username)
            otp_obj = ForgotPasswordOTP.objects.get(user=user, otp=otp, is_used=False)
        except (User.DoesNotExist, ForgotPasswordOTP.DoesNotExist):
            return Response(
                {'error': 'Invalid OTP or username'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        if otp_obj.is_expired():
            return Response({'error': 'OTP expired'}, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            'message': 'OTP verified successfully',
            'username': username,
            'otp': otp
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'])
    def reset_password(self, request):
        """Step 3: Reset password with verified OTP"""
        serializer = ResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        username = serializer.validated_data['username']
        otp = serializer.validated_data['otp']
        new_password = serializer.validated_data['new_password']

        try:
            user = User.objects.get(username=username)
            otp_obj = ForgotPasswordOTP.objects.get(user=user, otp=otp, is_used=False)
        except (User.DoesNotExist, ForgotPasswordOTP.DoesNotExist):
            return Response(
                {'error': 'Invalid OTP or username'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        if otp_obj.is_expired():
            return Response({'error': 'OTP expired'}, status=status.HTTP_400_BAD_REQUEST)

        # Reset password
        user.set_password(new_password)
        user.save()

        # Mark OTP as used
        otp_obj.mark_used()

        # Delete all OTPs for this user
        ForgotPasswordOTP.objects.filter(user=user).delete()

        return Response({
            'message': 'Password reset successfully'
        }, status=status.HTTP_200_OK)

# Generic Model ViewSet with Dynamic Permissions
class DynamicModelViewSet(viewsets.ModelViewSet):
    """
    Base ViewSet that automatically handles model permissions
    Extend this for any model that needs permission control
    """
    permission_classes = [IsAuthenticated, ModelViewPermission]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        
        # If user doesn't have view permission, return empty queryset
        if not user.has_model_permission(self.queryset.model, 'view'):
            return queryset.none()
            
        return queryset

# Apply dynamic permissions to existing ViewSets
class UserViewSet(DynamicModelViewSet):
    """CRUD for Users with dynamic permissions"""
    queryset = User.objects.all()
    serializer_class = UserSerializer


    def get_serializer_class(self):
        if self.action == 'create':
            return UserCreateSerializer
        return UserSerializer

    def get_permissions(self):
        """Simplify permissions - use role-based checks instead of Django permissions"""
        if self.action == 'create':
            return [IsAuthenticated()]
        return [IsAuthenticated()]
    

    def create(self, request, *args, **kwargs):
        """Create user with role-based permissions"""
        serializer = UserCreateSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        current_user = request.user


        if current_user.role == 'retailer':
            return Response(
                {'error': 'You do not have permission to create users'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = UserCreateSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        
        
        # Add created_by field
        serializer.validated_data['created_by'] = request.user
        
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        
        return Response(
            serializer.data, 
            status=status.HTTP_201_CREATED, 
            headers=headers
        )
    

    def get_queryset(self):
        user = self.request.user
        
        if user.role == 'superadmin':
            return User.objects.all()
        elif user.role == 'admin':
            return User.objects.exclude(role='superadmin')
        elif user.role == 'master':
            return User.objects.filter(role__in=['master', 'dealer', 'retailer'])
        elif user.role == 'dealer':
            # Dealers can only see retailers they created
            return User.objects.filter(role='retailer', created_by=user)
        else:
            # Retailers can only see themselves
            return User.objects.filter(id=user.id)
    

    def destroy(self, request, *args, **kwargs):
        user_to_delete = self.get_object()
        current_user = request.user
        
        # Prevent users from deleting themselves
        if user_to_delete == current_user:
            return Response(
                {'error': 'You cannot delete your own account'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Role-based deletion permissions
        if user_to_delete.role == 'superadmin' and current_user.role != 'superadmin':
            return Response(
                {'error': 'Only Super Admin can delete Super Admin users'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if user_to_delete.role == 'admin' and current_user.role not in ['superadmin', 'admin']:
            return Response(
                {'error': 'Only Admin and Super Admin can delete Admin users'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if user_to_delete.role == 'master' and current_user.role not in ['superadmin', 'admin']:
            return Response(
                {'error': 'Only Admin and Super Admin can delete Master users'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Dealers can only delete retailers they created
        if user_to_delete.role == 'retailer' and current_user.role == 'dealer':
            if user_to_delete.created_by != current_user:
                return Response(
                    {'error': 'You can only delete retailers created by you'},
                    status=status.HTTP_403_FORBIDDEN
                )
        
        return super().destroy(request, *args, **kwargs)

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def my_profile(self, request):
        """Get current user's profile"""
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)

    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def change_password(self, request):
        """Change current user's password"""
        user = request.user
        current_password = request.data.get('current_password')
        new_password = request.data.get('new_password')
        
        if not user.check_password(current_password):
            return Response(
                {'error': 'Current password is incorrect'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user.set_password(new_password)
        user.save()
        
        return Response({'message': 'Password changed successfully'})

    @action(detail=False, methods=['get'], permission_classes=[IsAdminUser])
    def all_users(self, request):
        users = User.objects.all()
        serializer = self.get_serializer(users, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], permission_classes=[IsSuperAdmin])
    def change_role(self, request, pk=None):
        user = self.get_object()
        new_role = request.data.get('role')
        
        if new_role not in dict(User.ROLE_CHOICES):
            return Response(
                {'error': 'Invalid role'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user.role = new_role
        user.save()
        
        return Response({
            'message': f'User {user.username} role changed to {new_role}',
            'user': UserSerializer(user).data
        })

class WalletViewSet(DynamicModelViewSet):
    serializer_class = WalletSerializer
    queryset = Wallet.objects.all()

    def get_queryset(self):
        user = self.request.user
        if user.is_admin_user():
            return Wallet.objects.all()
        return Wallet.objects.filter(user=user)

class TransactionViewSet(DynamicModelViewSet):
    serializer_class = TransactionSerializer
    queryset = Transaction.objects.all()

    def get_queryset(self):
        user = self.request.user
        if user.is_admin_user():
            return Transaction.objects.all()
        return Transaction.objects.filter(wallet__user=user)

class BalanceRequestViewSet(DynamicModelViewSet):
    queryset = BalanceRequest.objects.all()

    def get_serializer_class(self):
        if self.action in ['create']:
            return BalanceRequestCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return BalanceRequestUpdateSerializer
        return BalanceRequestCreateSerializer

    def get_queryset(self):
        user = self.request.user
        if user.role == 'retailer':
            return BalanceRequest.objects.filter(retailer=user)
        elif user.is_admin_user():
            return BalanceRequest.objects.all()
        return BalanceRequest.objects.none()

    def perform_create(self, serializer):
        if self.request.user.role != 'retailer':
            raise serializers.ValidationError("Only retailers can create balance requests")
        serializer.save(retailer=self.request.user)

    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def approve(self, request, pk=None):
        balance_request = self.get_object()
        
        if balance_request.status != 'pending':
            return Response(
                {'error': 'This request has already been processed'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            with db_transaction.atomic():
                balance_request.status = 'approved'
                balance_request.processed_by = request.user
                balance_request.admin_notes = request.data.get('admin_notes', '')
                balance_request.save()

                wallet = Wallet.objects.select_for_update().get(user=balance_request.retailer)
                wallet.balance += balance_request.amount
                wallet.save()
                
                Transaction.objects.create(
                    wallet=wallet,
                    amount=balance_request.amount,
                    transaction_type='credit',
                    description=f"Balance request approved: {balance_request.description}",
                    balance_request=balance_request,
                    created_by=request.user
                )

                return Response({
                    'message': 'Balance request approved and amount added to wallet',
                    'new_balance': wallet.balance,
                    'retailer': balance_request.retailer.username
                })
                
        except Wallet.DoesNotExist:
            return Response({'error': 'Wallet not found'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def reject(self, request, pk=None):
        balance_request = self.get_object()
        
        if balance_request.status != 'pending':
            return Response(
                {'error': 'This request has already been processed'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        balance_request.status = 'rejected'
        balance_request.processed_by = request.user
        balance_request.admin_notes = request.data.get('admin_notes', 'Request rejected')
        balance_request.save()

        return Response({
            'message': 'Balance request rejected',
            'retailer': balance_request.retailer.username
        })