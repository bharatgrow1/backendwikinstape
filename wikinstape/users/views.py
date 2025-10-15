from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from .models import User, EmailOTP
from .serializers import LoginSerializer, OTPVerifySerializer, UserSerializer
from .utils import send_otp_email


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
        send_otp_email(user.email, otp)

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
            'role': user.role
        }, status=status.HTTP_200_OK)


class UserViewSet(viewsets.ModelViewSet):
    """Optional: CRUD for Users"""
    queryset = User.objects.all()
    serializer_class = UserSerializer

