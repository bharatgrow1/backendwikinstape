from django.db import transaction as db_transaction
from django.utils import timezone
from decimal import Decimal
import logging
from .eko_service import eko_service
from dmt.models import DMTTransaction
from users.models import Transaction

logger = logging.getLogger(__name__)

class DMTManager:
    def __init__(self):
        self.eko_service = eko_service


    def calculate_dmt_charges(self, amount):
        """Calculate DMT service charges"""
        if amount <= 10000:
            base_fee = Decimal('10.00')
        else:
            base_fee = Decimal('15.00')
        
        gst = (base_fee * Decimal('0.18')).quantize(Decimal('0.01'))
        
        total_fee = base_fee + gst
        
        return {
            'base_fee': base_fee,
            'gst': gst,
            'total_fee': total_fee,
            'total_amount': amount + total_fee
        }
    


    def verify_wallet_for_dmt(self, user, amount, pin):
        """Verify wallet has sufficient balance for DMT"""
        try:
            wallet = user.wallet
            
            charges = self.calculate_dmt_charges(amount)
            total_deduction = charges['total_amount']
            
            if not wallet.verify_pin(pin):
                return False, "Invalid wallet PIN", None
            
            if not wallet.has_sufficient_balance(amount, charges['total_fee']):
                return False, f"Insufficient wallet balance. Required: ₹{total_deduction} (₹{amount} transfer + ₹{charges['total_fee']} fees)", None
            
            return True, "OK", charges
            
        except Exception as e:
            logger.error(f"Wallet verification error: {str(e)}")
            return False, f"Wallet verification failed: {str(e)}", None
    

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

    @db_transaction.atomic
    def initiate_transaction(self, customer_id, recipient_id, amount, otp, otp_ref_id, user, pin):
        """Initiate transaction with wallet deduction"""
        try:
            wallet_ok, wallet_msg, charges = self.verify_wallet_for_dmt(user, Decimal(str(amount)), pin)
            if not wallet_ok:
                return {"status": 1, "message": wallet_msg}
            
            wallet = user.wallet
            total_deduction = charges['total_amount']
            
            try:
                wallet.deduct_amount(Decimal(str(amount)), charges['total_fee'], pin)
                
                wallet_transaction = Transaction.objects.create(
                    wallet=wallet,
                    amount=Decimal(str(amount)),
                    service_charge=charges['total_fee'],
                    net_amount=Decimal(str(amount)),
                    transaction_type='debit',
                    transaction_category='dmt_transfer',
                    description=f"DMT to recipient {recipient_id}",
                    created_by=user,
                    status='processing',
                    metadata={
                        'customer_id': customer_id,
                        'recipient_id': recipient_id,
                        'otp_ref_id': otp_ref_id,
                        'base_fee': str(charges['base_fee']),
                        'gst': str(charges['gst']),
                        'total_fee': str(charges['total_fee'])
                    }
                )
                
                logger.info(f"✅ Wallet deduction successful: ₹{total_deduction} from {user.username}")
                
            except ValueError as e:
                return {"status": 1, "message": f"Payment failed: {str(e)}"}
            
            eko_response = self.eko_service.initiate_transaction(
                customer_id=customer_id,
                recipient_id=recipient_id,
                amount=amount,
                otp=otp,
                otp_ref_id=otp_ref_id
            )
            
            dmt_transaction = DMTTransaction.objects.create(
                user=user,
                amount=Decimal(str(amount)),
                service_charge=charges['total_fee'],
                total_amount=total_deduction,
                sender_mobile=customer_id,
                eko_recipient_id=recipient_id,
                status='processing',
                wallet_transaction=wallet_transaction,
                api_response=eko_response
            )
            
            if eko_response.get('status') == 0:
                data = eko_response.get('data', {})
                
                dmt_transaction.eko_tid = data.get('tid')
                dmt_transaction.client_ref_id = data.get('client_ref_id')
                dmt_transaction.eko_tx_status = data.get('tx_status')
                dmt_transaction.eko_txstatus_desc = data.get('txstatus_desc')
                dmt_transaction.eko_bank_ref_num = data.get('bank_ref_num')
                
                if data.get('tx_status') == '0':
                    dmt_transaction.status = 'success'
                    wallet_transaction.status = 'success'
                    wallet_transaction.save()
                    
                    self.process_dmt_commission(user, Decimal(str(amount)), dmt_transaction)
                    
                    return {
                        "status": 0,
                        "message": "Transaction successful",
                        "transaction_id": dmt_transaction.transaction_id,
                        "eko_tid": dmt_transaction.eko_tid,
                        "bank_ref_num": dmt_transaction.eko_bank_ref_num,
                        "wallet_balance": wallet.balance
                    }
                else:
                    dmt_transaction.status = 'failed'
                    dmt_transaction.status_message = data.get('txstatus_desc', 'Transaction failed')
                    dmt_transaction.save()
                    
                    wallet.add_amount(total_deduction)
                    wallet_transaction.status = 'failed'
                    wallet_transaction.description = f"Refund: {wallet_transaction.description}"
                    wallet_transaction.save()
                    
                    Transaction.objects.create(
                        wallet=wallet,
                        amount=total_deduction,
                        transaction_type='credit',
                        transaction_category='refund',
                        description=f"Refund for failed DMT transaction {dmt_transaction.transaction_id}",
                        created_by=user,
                        status='success'
                    )
                    
                    return {
                        "status": 1,
                        "message": f"Transaction failed: {data.get('txstatus_desc', 'Unknown error')}. Amount refunded.",
                        "wallet_balance": wallet.balance
                    }
            else:
                # EKO API call failed
                dmt_transaction.status = 'failed'
                dmt_transaction.status_message = eko_response.get('message', 'API call failed')
                dmt_transaction.save()
                
                # Refund wallet
                wallet.add_amount(total_deduction)
                wallet_transaction.status = 'failed'
                wallet_transaction.description = f"Refund: {wallet_transaction.description}"
                wallet_transaction.save()
                
                Transaction.objects.create(
                    wallet=wallet,
                    amount=total_deduction,
                    transaction_type='credit',
                    transaction_category='refund',
                    description=f"Refund for failed DMT API call {dmt_transaction.transaction_id}",
                    created_by=user,
                    status='success'
                )
                
                return {
                    "status": 1,
                    "message": f"Transaction failed: {eko_response.get('message', 'API error')}. Amount refunded.",
                    "wallet_balance": wallet.balance
                }
                
        except Exception as e:
            logger.error(f"DMT transaction error: {str(e)}")
            return {"status": 1, "message": f"Transaction failed: {str(e)}"}
        



    def process_dmt_commission(self, user, amount, dmt_transaction):
        """Process commission for DMT transaction"""
        try:
            from commission.views import CommissionManager
            from services.models import ServiceSubCategory
            
            # Find DMT service
            dmt_service = ServiceSubCategory.objects.filter(
                name__icontains='dmt',
                is_active=True
            ).first()
            
            if dmt_service:
                # Create dummy service submission for commission
                class DummyServiceSubmission:
                    def __init__(self, user, amount, dmt_transaction):
                        self.submitted_by = user
                        self.amount = amount
                        self.service_subcategory = dmt_service
                        self.service_form = type('obj', (object,), {
                            'name': f"DMT Transfer - {dmt_transaction.transaction_id}"
                        })()
                        self.submission_id = dmt_transaction.transaction_id
                
                dummy_submission = DummyServiceSubmission(user, amount, dmt_transaction)
                
                # Get wallet transaction
                wallet_transaction = dmt_transaction.wallet_transaction
                
                # Process commission
                success, comm_message = CommissionManager.process_service_commission(
                    dummy_submission, wallet_transaction
                )
                
                if success:
                    logger.info(f"✅ DMT commission processed: {dmt_transaction.transaction_id}")
                    dmt_transaction.status_message = f"Transaction successful. {comm_message}"
                else:
                    logger.warning(f"⚠️ DMT commission failed: {comm_message}")
                    dmt_transaction.status_message = f"Transaction successful but commission failed: {comm_message}"
                
                dmt_transaction.save()
                
        except ImportError:
            logger.warning("Commission app not available")
        except Exception as e:
            logger.error(f"❌ Commission processing error: {str(e)}")

    
    def transaction_inquiry(self, inquiry_id, is_client_ref_id=False):
        """Check transaction status by TID or client_ref_id"""
        try:
            response = self.eko_service.transaction_inquiry(inquiry_id, is_client_ref_id)
            
            # Optionally update transaction status in database
            if response.get('status') == 0:
                data = response.get('data', {})
                tx_status = data.get('tx_status')
                
                # Update transaction record if exists
                try:
                    if is_client_ref_id:
                        transaction = DMTTransaction.objects.filter(
                            client_ref_id=inquiry_id
                        ).first()
                    else:
                        transaction = DMTTransaction.objects.filter(
                            eko_tid=inquiry_id
                        ).first()
                    
                    if transaction:
                        transaction.update_from_eko_response(response)
                except Exception as e:
                    logger.error(f"Failed to update transaction record: {str(e)}")
            
            return response
            
        except Exception as e:
            logger.error(f"Transaction inquiry error: {str(e)}")
            return {"status": 1, "message": f"Failed to check transaction status: {str(e)}"}
    

    def refund_transaction(self, tid, otp):
        """Process refund for transaction"""
        try:
            # First verify the transaction exists and is eligible for refund
            try:
                transaction = DMTTransaction.objects.filter(eko_tid=tid).first()
                if not transaction:
                    return {"status": 1, "message": "Transaction not found"}
                
                if transaction.status not in ['failed', 'processing']:
                    return {"status": 1, "message": "Transaction is not eligible for refund"}
            except DMTTransaction.DoesNotExist:
                return {"status": 1, "message": "Transaction not found"}
            
            # Process refund through EKO API
            response = self.eko_service.refund_transaction(tid, otp)
            
            # Update transaction status based on refund response
            if response.get('status') == 0:
                transaction.status = 'cancelled'
                transaction.status_message = "Refund initiated"
                transaction.save()
            
            return response
            
        except Exception as e:
            logger.error(f"Refund transaction error: {str(e)}")
            return {"status": 1, "message": f"Failed to process refund: {str(e)}"}
    

    def resend_refund_otp(self, tid):
        """Resend OTP for refund"""
        try:
            response = self.eko_service.resend_refund_otp(tid)
            return response
        except Exception as e:
            logger.error(f"Resend refund OTP error: {str(e)}")
            return {"status": 1, "message": f"Failed to resend refund OTP: {str(e)}"}


dmt_manager = DMTManager()