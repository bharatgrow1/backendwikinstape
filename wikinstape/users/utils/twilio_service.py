# users/utils/twilio_service.py
from twilio.rest import Client
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class TwilioService:
    def __init__(self):
        self.account_sid = settings.TWILIO_ACCOUNT_SID
        self.auth_token = settings.TWILIO_AUTH_TOKEN
        self.verify_service_sid = settings.TWILIO_VERIFY_SERVICE_SID
        try:
            self.client = Client(self.account_sid, self.auth_token)
            logger.info("✅ Twilio client initialized successfully")
        except Exception as e:
            logger.error(f"❌ Twilio client initialization failed: {e}")
            self.client = None

    def send_otp_sms(self, mobile):
        """Send OTP via SMS using Twilio Verify"""
        try:
            if not self.client:
                return {
                    'success': False,
                    'error': 'Twilio client not initialized'
                }

            # Format mobile number for Twilio
            if not mobile.startswith('+'):
                if mobile.startswith('91'):
                    mobile = '+' + mobile
                else:
                    mobile = '+91' + mobile

            logger.info(f"🔧 Sending OTP to: {mobile}")

            # Send verification
            verification = self.client.verify \
                .v2 \
                .services(self.verify_service_sid) \
                .verifications \
                .create(to=mobile, channel='sms')

            logger.info(f"✅ OTP sent successfully! SID: {verification.sid}")
            
            return {
                'success': True,
                'sid': verification.sid,
                'status': verification.status
            }
            
        except Exception as e:
            logger.error(f"❌ Twilio OTP send failed: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    def verify_otp(self, mobile, otp):
        """Verify OTP using Twilio Verify"""
        try:
            if not self.client:
                return {
                    'success': False,
                    'error': 'Twilio client not initialized'
                }

            # Format mobile number
            if not mobile.startswith('+'):
                if mobile.startswith('91'):
                    mobile = '+' + mobile
                else:
                    mobile = '+91' + mobile

            verification_check = self.client.verify \
                .v2 \
                .services(self.verify_service_sid) \
                .verification_checks \
                .create(to=mobile, code=otp)

            return {
                'success': True,
                'valid': verification_check.status == 'approved',
                'status': verification_check.status
            }
        except Exception as e:
            logger.error(f"❌ Twilio OTP verification failed: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

# Global instance
twilio_service = TwilioService()