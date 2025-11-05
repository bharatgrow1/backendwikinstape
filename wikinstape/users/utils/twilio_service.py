from twilio.rest import Client
from django.conf import settings


class TwilioService:
    def __init__(self):
        self.account_sid = settings.TWILIO_ACCOUNT_SID
        self.auth_token = settings.TWILIO_AUTH_TOKEN
        self.verify_service_sid = settings.TWILIO_VERIFY_SERVICE_SID
        self.client = Client(self.account_sid, self.auth_token)

    def send_otp_sms(self, mobile):
        """Send OTP via SMS using Twilio Verify"""
        try:
            print(f"🔧 DEBUG: Starting OTP send for: {mobile}")
            
            # Format mobile number
            if not mobile.startswith('+'):
                if mobile.startswith('91'):
                    mobile = '+' + mobile
                else:
                    mobile = '+91' + mobile

            print(f"🔧 DEBUG: Formatted mobile: {mobile}")
            print(f"🔧 DEBUG: Using Service SID: {self.verify_service_sid}")

            # Test Twilio connection
            try:
                service = self.client.verify.v2.services(self.verify_service_sid).fetch()
                print(f"🔧 DEBUG: Twilio service found: {service.friendly_name}")
            except Exception as e:
                print(f"🔧 DEBUG: Twilio service error: {e}")
                return {
                    'success': False,
                    'error': f'Twilio service error: {str(e)}'
                }

            # Send verification
            print(f"🔧 DEBUG: Sending verification to: {mobile}")
            verification = self.client.verify \
                .v2 \
                .services(self.verify_service_sid) \
                .verifications \
                .create(to=mobile, channel='sms')

            print(f"🔧 DEBUG: OTP sent successfully! SID: {verification.sid}")
            
            return {
                'success': True,
                'sid': verification.sid,
                'status': verification.status
            }
            
        except Exception as e:
            print(f"🔧 DEBUG: Twilio OTP send failed: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    def verify_otp(self, mobile, otp):
        """Verify OTP using Twilio Verify"""
        try:
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
            return {
                'success': False,
                'error': str(e)
            }

twilio_service = TwilioService()