from django.db import transaction as db_transaction
from django.utils import timezone
from decimal import Decimal
import logging
from ..models import DMTTransaction, DMTRecipient, DMTSenderProfile
from .eko_service import eko_service
from users.models import Wallet, Transaction

logger = logging.getLogger(__name__)

class DMTManager:
    def __init__(self):
        self.eko_service = eko_service

    def get_sender_profile(self, mobile_number):
        """Get or create sender profile"""
        try:
            # Check EKO API for sender profile
            response = self.eko_service.get_sender_profile(mobile_number)
            
            if response.get('status') == 0:
                # Sender exists in EKO system
                profile_data = response.get('data', {})
                return True, "Sender profile found", profile_data
            else:
                # Sender not found, needs KYC
                return False, "Sender not registered. KYC required.", None
                
        except Exception as e:
            logger.error(f"Error getting sender profile: {str(e)}")
            return False, f"Error checking sender profile: {str(e)}", None

    def register_sender_biometric_kyc(self, user, mobile, aadhar, piddata):
        """Register sender using biometric KYC"""
        try:
            response = self.eko_service.customer_ekyc_biometric(mobile, aadhar, piddata)
            
            if response.get('status') == 0:
                # KYC initiated successfully
                kyc_data = response.get('data', {})
                
                # Create or update sender profile
                sender_profile, created = DMTSenderProfile.objects.get_or_create(
                    user=user,
                    defaults={
                        'mobile': mobile,
                        'aadhar_number': aadhar,
                        'kyc_status': 'verified',
                        'kyc_method': 'biometric',
                        'kyc_verified_at': timezone.now(),
                        'eko_customer_id': mobile,
                        'eko_profile_data': kyc_data
                    }
                )
                
                if not created:
                    sender_profile.aadhar_number = aadhar
                    sender_profile.kyc_status = 'verified'
                    sender_profile.kyc_method = 'biometric'
                    sender_profile.kyc_verified_at = timezone.now()
                    sender_profile.eko_customer_id = mobile
                    sender_profile.eko_profile_data = kyc_data
                    sender_profile.save()
                
                return True, "Biometric KYC completed successfully", sender_profile
            else:
                error_message = response.get('message', 'KYC failed')
                return False, error_message, None
                
        except Exception as e:
            logger.error(f"Error in biometric KYC: {str(e)}")
            return False, f"KYC processing failed: {str(e)}", None

    def verify_sender_kyc_otp(self, customer_id, otp, otp_ref_id, kyc_request_id):
        """Verify sender KYC OTP"""
        try:
            response = self.eko_service.verify_ekyc_otp(customer_id, otp, otp_ref_id, kyc_request_id)
            
            if response.get('status') == 0:
                return True, "KYC verification successful", response.get('data', {})
            else:
                error_message = response.get('message', 'OTP verification failed')
                return False, error_message, None
                
        except Exception as e:
            logger.error(f"Error in KYC OTP verification: {str(e)}")
            return False, f"OTP verification failed: {str(e)}", None

    def add_recipient(self, user, recipient_data):
        """Add recipient to EKO and local database"""
        try:
            # Get sender profile
            sender_profile = DMTSenderProfile.objects.get(user=user)
            
            # Add recipient to EKO
            response = self.eko_service.add_recipient(
                customer_id=sender_profile.mobile,
                recipient_name=recipient_data['name'],
                recipient_mobile=recipient_data.get('mobile', ''),
                account=recipient_data['account_number'],
                ifsc=recipient_data['ifsc_code'],
                bank_id=recipient_data.get('bank_id', 11),
                recipient_type=recipient_data.get('recipient_type', 3),
                account_type=recipient_data.get('account_type', 1)
            )
            
            if response.get('status') == 0:
                recipient_id = response.get('data', {}).get('recipient_id')
                
                # Create recipient in local database
                recipient = DMTRecipient.objects.create(
                    user=user,
                    name=recipient_data['name'],
                    mobile=recipient_data.get('mobile', ''),
                    account_number=recipient_data['account_number'],
                    ifsc_code=recipient_data['ifsc_code'],
                    bank_name=recipient_data.get('bank_name', ''),
                    bank_id=recipient_data.get('bank_id', 11),
                    account_type=recipient_data.get('account_type', 1),
                    recipient_type=recipient_data.get('recipient_type', 3),
                    eko_recipient_id=recipient_id
                )
                
                recipient.mark_verified(recipient_id, response)
                return True, "Recipient added successfully", recipient
            else:
                error_message = response.get('message', 'Failed to add recipient')
                return False, error_message, None
                
        except DMTSenderProfile.DoesNotExist:
            return False, "Sender profile not found. Please complete KYC first.", None
        except Exception as e:
            logger.error(f"Error adding recipient: {str(e)}")
            return False, f"Failed to add recipient: {str(e)}", None

    def initiate_transaction(self, user, transaction_data):
        """Initiate DMT transaction"""
        try:
            with db_transaction.atomic():
                sender_profile = DMTSenderProfile.objects.get(user=user)
                recipient = DMTRecipient.objects.get(
                    recipient_id=transaction_data['recipient_id'],
                    user=user,
                    is_verified=True
                )
                
                amount = transaction_data['amount']
                service_charge = transaction_data['service_charge']
                total_amount = amount + service_charge
                
                # Deduct amount from wallet
                wallet = user.wallet
                wallet.deduct_amount(amount, service_charge, transaction_data['pin'])
                
                # Create transaction record
                dmt_transaction = DMTTransaction.objects.create(
                    user=user,
                    amount=amount,
                    service_charge=service_charge,
                    total_amount=total_amount,
                    transaction_type=transaction_data.get('transaction_type', 'imps'),
                    sender_mobile=sender_profile.mobile,
                    sender_name=user.get_full_name() or user.username,
                    sender_aadhar=sender_profile.aadhar_number,
                    recipient=recipient,
                    recipient_name=recipient.name,
                    recipient_mobile=recipient.mobile,
                    recipient_account=recipient.account_number,
                    recipient_ifsc=recipient.ifsc_code,
                    recipient_bank=recipient.bank_name,
                    eko_customer_id=sender_profile.mobile,
                    eko_recipient_id=recipient.eko_recipient_id,
                    status='initiated'
                )
                
                # Send transaction OTP via EKO
                response = self.eko_service.send_transaction_otp(
                    customer_id=sender_profile.mobile,
                    recipient_id=recipient.eko_recipient_id,
                    amount=float(amount)
                )
                
                if response.get('status') == 0:
                    otp_ref_id = response.get('data', {}).get('otp_ref_id')
                    dmt_transaction.mark_otp_sent(otp_ref_id)
                    
                    return True, "OTP sent successfully", dmt_transaction
                else:
                    # Refund wallet if OTP sending fails
                    wallet.add_amount(total_amount)
                    dmt_transaction.mark_failed(
                        response.get('message', 'Failed to send OTP'),
                        response
                    )
                    return False, "Failed to send OTP", dmt_transaction
                    
        except Exception as e:
            logger.error(f"Error initiating transaction: {str(e)}")
            return False, f"Transaction initiation failed: {str(e)}", None

    def verify_and_process_transaction(self, user, verification_data):
        """Verify OTP and process transaction"""
        try:
            with db_transaction.atomic():
                dmt_transaction = DMTTransaction.objects.get(
                    transaction_id=verification_data['transaction_id'],
                    user=user,
                    status='otp_sent'
                )
                
                # Verify OTP and process transaction via EKO
                response = self.eko_service.initiate_transaction(
                    customer_id=dmt_transaction.eko_customer_id,
                    recipient_id=dmt_transaction.eko_recipient_id,
                    amount=float(dmt_transaction.amount),
                    otp=verification_data['otp'],
                    otp_ref_id=dmt_transaction.eko_otp_ref_id
                )
                
                if response.get('status') == 0:
                    transaction_ref = response.get('data', {}).get('transaction_id')
                    
                    # Update sender usage
                    sender_profile = DMTSenderProfile.objects.get(user=user)
                    sender_profile.update_usage(dmt_transaction.amount)
                    
                    # Mark transaction as success
                    dmt_transaction.mark_success(transaction_ref)
                    dmt_transaction.api_response = response
                    dmt_transaction.save()
                    
                    # Create commission transaction
                    self._create_commission_transaction(dmt_transaction)
                    
                    return True, "Transaction completed successfully", dmt_transaction
                else:
                    # Refund wallet if transaction fails
                    wallet = user.wallet
                    wallet.add_amount(dmt_transaction.total_amount)
                    
                    dmt_transaction.mark_failed(
                        response.get('message', 'Transaction failed'),
                        response
                    )
                    return False, "Transaction failed", dmt_transaction
                    
        except DMTTransaction.DoesNotExist:
            return False, "Transaction not found", None
        except Exception as e:
            logger.error(f"Error processing transaction: {str(e)}")
            return False, f"Transaction processing failed: {str(e)}", None

    def _create_commission_transaction(self, dmt_transaction):
        """Create commission transaction for DMT service"""
        try:
            from commission.models import CommissionTransaction, ServiceCommission
            from commission.views import CommissionManager
            
            # Find DMT service commission configuration
            dmt_service_commission = ServiceCommission.objects.filter(
                service_subcategory__name__icontains='money transfer',
                is_active=True
            ).first()
            
            if dmt_service_commission:
                # Use existing commission manager to process commission
                success, message = CommissionManager.process_service_commission(
                    None,  # No service submission for DMT
                    self._create_wallet_transaction_for_commission(dmt_transaction)
                )
                
                if not success:
                    logger.warning(f"Commission processing failed for DMT: {message}")
                    
        except Exception as e:
            logger.error(f"Error creating commission transaction: {str(e)}")

    def _create_wallet_transaction_for_commission(self, dmt_transaction):
        """Create wallet transaction for commission calculation"""
        from users.models import Transaction
        
        return Transaction.objects.create(
            wallet=dmt_transaction.user.wallet,
            amount=dmt_transaction.amount,
            transaction_type='debit',
            transaction_category='money_transfer',
            description=f"DMT Transfer to {dmt_transaction.recipient_name}",
            created_by=dmt_transaction.user,
            status='success'
        )

    def get_transaction_status(self, transaction_id):
        """Get transaction status"""
        try:
            dmt_transaction = DMTTransaction.objects.get(transaction_id=transaction_id)
            return True, "Status retrieved", dmt_transaction
        except DMTTransaction.DoesNotExist:
            return False, "Transaction not found", None

    def get_recipients(self, user):
        """Get user's recipients"""
        try:
            recipients = DMTRecipient.objects.filter(user=user, is_active=True)
            return True, "Recipients retrieved", recipients
        except Exception as e:
            logger.error(f"Error getting recipients: {str(e)}")
            return False, f"Failed to get recipients: {str(e)}", None

dmt_manager = DMTManager()