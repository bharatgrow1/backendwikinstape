from django.db import transaction as db_transaction
from django.utils import timezone
from decimal import Decimal
import logging
from .eko_service import eko_service

logger = logging.getLogger(__name__)

class DMTManager:
    def __init__(self):
        self.eko_service = eko_service

    def onboard_user(self, user_data):
        """Onboard user to EKO system"""
        return self.eko_service.onboard_user(user_data)
    

    def verify_customer_identity(self, customer_mobile, otp, otp_ref_id):
        """Verify customer identity with OTP"""
        return self.eko_service.verify_customer_identity(customer_mobile, otp, otp_ref_id)


    def resend_otp(self, customer_mobile):
        """Resend OTP for customer verification"""
        return self.eko_service.resend_otp(customer_mobile)
    

    def create_customer(self, customer_data):
        """Create new customer for DMT"""
        return self.eko_service.create_customer(customer_data)
    

    def get_sender_profile(self, customer_mobile):
        """Get sender profile"""
        return self.eko_service.get_sender_profile(customer_mobile)

    def customer_ekyc_biometric(self, customer_id, aadhar, piddata):
        """Biometric KYC"""
        return self.eko_service.customer_ekyc_biometric(customer_id, aadhar, piddata)

    def verify_ekyc_otp(self, customer_id, otp, otp_ref_id, kyc_request_id):
        """Verify KYC OTP"""
        return self.eko_service.verify_ekyc_otp(customer_id, otp, otp_ref_id, kyc_request_id)

    def add_recipient(self, customer_id, recipient_data):
        """Add recipient"""
        return self.eko_service.add_recipient(
            customer_id=customer_id,
            recipient_name=recipient_data['recipient_name'],
            recipient_mobile=recipient_data.get('recipient_mobile', ''),
            account=recipient_data['account'],
            ifsc=recipient_data['ifsc'],
            bank_id=recipient_data.get('bank_id', 11),
            recipient_type=recipient_data.get('recipient_type', 3),
            account_type=recipient_data.get('account_type', 1)
        )

    def get_recipient_list(self, customer_id):
        """Get recipient list"""
        return self.eko_service.get_recipient_list(customer_id)

    def send_transaction_otp(self, customer_id, recipient_id, amount):
        """Send transaction OTP"""
        return self.eko_service.send_transaction_otp(customer_id, recipient_id, amount)

    def initiate_transaction(self, customer_id, recipient_id, amount, otp, otp_ref_id):
        """Initiate transaction"""
        return self.eko_service.initiate_transaction(
            customer_id=customer_id,
            recipient_id=recipient_id,
            amount=amount,
            otp=otp,
            otp_ref_id=otp_ref_id
        )
    
    def transaction_inquiry(self, inquiry_id, is_client_ref_id=False):
        """Check transaction status by TID or client_ref_id"""
        return self.eko_service.transaction_inquiry(inquiry_id, is_client_ref_id)

dmt_manager = DMTManager()