from django.db import transaction as db_transaction
from django.utils import timezone
from decimal import Decimal
import logging
from .eko_service import eko_service
from dmt.models import DMTTransaction

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
        

    def initiate_transaction_with_wallet(self, user, transaction_data):
        """
        DMT transaction with wallet deduction
        """
        try:
            with db_transaction.atomic():
                wallet = user.wallet
                
                transfer_amount = Decimal(str(transaction_data['amount']))
                processing_fee = Decimal('7.00')
                gst = Decimal('1.26')
                total_fee = processing_fee + gst
                total_deduction = transfer_amount + total_fee
                
                logger.info(f"💰 DMT Payment Calculation:")
                logger.info(f"   Transfer Amount: ₹{transfer_amount}")
                logger.info(f"   Processing Fee: ₹{processing_fee}")
                logger.info(f"   GST: ₹{gst}")
                logger.info(f"   Total Fee: ₹{total_fee}")
                logger.info(f"   Total Deduction: ₹{total_deduction}")
                logger.info(f"   Wallet Balance: ₹{wallet.balance}")
                
                pin = transaction_data.get('pin')
                if not pin:
                    return {
                        "status": 1,
                        "message": "Wallet PIN is required"
                    }
                
                if not wallet.verify_pin(pin):
                    return {
                        "status": 1,
                        "message": "Invalid wallet PIN"
                    }
                
                if wallet.balance < total_deduction:
                    return {
                        "status": 1,
                        "message": f"Insufficient wallet balance. Required: ₹{total_deduction} (₹{transfer_amount} transfer + ₹{total_fee} fees), Available: ₹{wallet.balance}"
                    }
                
                wallet.deduct_amount(transfer_amount, total_fee, pin)
                
                dmt_transaction = DMTTransaction.objects.create(
                    user=user,
                    amount=transfer_amount,

                    service_charge=total_fee,
                    total_amount=total_deduction,

                    sender_mobile=transaction_data.get('customer_id'),

                    recipient_name=transaction_data.get('recipient_name'),
                    recipient_account=transaction_data.get('account'),
                    recipient_ifsc=transaction_data.get('ifsc'),

                    status='initiated'
                )

                
                from users.models import Transaction
                Transaction.objects.create(
                    wallet=wallet,
                    amount=transfer_amount,
                    service_charge=total_fee,
                    net_amount=transfer_amount,
                    transaction_type='debit',
                    transaction_category='dmt_transfer',
                    description=f"DMT transfer to {transaction_data.get('recipient_name')}",
                    created_by=user,
                    status='success',
                    metadata={
                        'dmt_transaction_id': dmt_transaction.id,
                        'recipient_name': transaction_data.get('recipient_name'),
                        'recipient_account': transaction_data.get('account')[-4:],
                        'ifsc': transaction_data.get('ifsc'),
                        'transfer_amount': str(transfer_amount),
                        'fee': str(total_fee),
                        'total_deduction': str(total_deduction)
                    }
                )
                
                logger.info(f"✅ Wallet deduction successful: ₹{total_deduction} deducted")
                logger.info(f"✅ New wallet balance: ₹{wallet.balance}")
                
                eko_data = {
                    'customer_id': transaction_data.get('customer_id'),
                    'recipient_id': transaction_data.get('recipient_id'),
                    'amount': str(transfer_amount),
                    'otp': transaction_data.get('otp'),
                    'otp_ref_id': transaction_data.get('otp_ref_id')
                }
                
                logger.info(f"📤 Sending to EKO: Transfer Amount = ₹{transfer_amount}")
                eko_result = self.eko_service.initiate_transaction(**eko_data)
                
                logger.info(f"✅ EKO DMT response: {eko_result}")
                
                if eko_result.get('status') == 0:
                    dmt_transaction.status = 'success'
                    dmt_transaction.eko_tid = eko_result.get('data', {}).get('tid')
                    dmt_transaction.client_ref_id = eko_result.get('data', {}).get('client_ref_id')
                    dmt_transaction.bank_ref_num = eko_result.get('data', {}).get('bank_ref_num')
                    dmt_transaction.save()
                    
                    return {
                        "status": 0,
                        "message": "DMT transfer successful",
                        "data": {
                            "transaction_id": dmt_transaction.id,
                            "client_ref_id": dmt_transaction.client_ref_id,
                            "amount": str(transfer_amount),
                            "fee": str(processing_fee),
                            "gst": str(gst),
                            "total_fee": str(total_fee),
                            "total_deduction": str(total_deduction),
                            "balance": str(wallet.balance),
                            "recipient_name": transaction_data.get('recipient_name'),
                            "bank_ref_num": dmt_transaction.bank_ref_num
                        }
                    }
                else:
                    logger.error(f"DMT transfer failed: {eko_result.get('message')}")
                    
                    wallet.add_amount(total_deduction)
                    
                    Transaction.objects.create(
                        wallet=wallet,
                        amount=total_deduction,
                        transaction_type='credit',
                        transaction_category='refund',
                        description=f"Refund for failed DMT transfer to {transaction_data.get('recipient_name')}",
                        created_by=user,
                        status='success',
                        metadata={
                            'dmt_transaction_id': dmt_transaction.id,
                            'error': eko_result.get('message')
                        }
                    )
                    
                    dmt_transaction.status = 'failed'
                    dmt_transaction.status_message = eko_result.get('message')
                    dmt_transaction.save()
                    
                    return {
                        "status": 1,
                        "message": f"DMT transfer failed: {eko_result.get('message')}. ₹{total_deduction} refunded to wallet.",
                        "data": {
                            "balance": str(wallet.balance)
                        }
                    }
                    
        except Exception as e:
            logger.error(f"DMT wallet payment error: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            
            return {
                "status": 1,
                "message": f"Payment processing failed: {str(e)}"
            }


dmt_manager = DMTManager()