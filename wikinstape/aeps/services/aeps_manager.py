import time
from .aeps_service import EkoAEPSService
from ..models import AEPSMerchant, AEPSTransaction
from django.utils import timezone


class AEPSManager:
    def __init__(self, user_code=None):
        self.eko = EkoAEPSService(user_code)
        self.user_code = user_code
    
    def onboard_merchant(self, merchant_data):
        """Onboard a new merchant and save to database"""
        # Call EKO API
        api_response = self.eko.onboard_merchant(merchant_data)
        
        if api_response.get('response_status_id') == 0:  # Success
            user_code = api_response.get('data', {}).get('user_code')
            
            # Save merchant to database
            merchant = AEPSMerchant.objects.create(
                user_code=user_code,
                merchant_name=f"{merchant_data['first_name']} {merchant_data.get('last_name', '')}",
                shop_name=merchant_data['shop_name'],
                mobile=merchant_data['mobile'],
                email=merchant_data['email'],
                pan_number=merchant_data['pan_number'],
                address_line=merchant_data['address_line'],
                city=merchant_data['city'],
                state=merchant_data['state'],
                pincode=merchant_data['pincode'],
                district=merchant_data.get('district', ''),
                area=merchant_data.get('area', '')
            )
            
            # Update user_code for future requests
            self.user_code = user_code
            self.eko.user_code = user_code
            
            return {
                'success': True,
                'user_code': user_code,
                'merchant_id': merchant.id,
                'message': api_response.get('message', 'Merchant onboarded successfully')
            }
        else:
            return {
                'success': False,
                'message': api_response.get('message', 'Onboarding failed'),
                'error': api_response
            }
    
    def initiate_cash_withdrawal(self, transaction_data):
        """Initiate cash withdrawal transaction"""
        client_ref_id = f"AEPSCW{int(time.time())}{transaction_data['aadhaar_number'][-4:]}"
        
        payload = {
            "client_ref_id": client_ref_id,
            "amount": transaction_data['amount'],
            "aadhaar_number": transaction_data['aadhaar_number'],
            "bank_identifier": transaction_data['bank_identifier'],
            "latitude": transaction_data.get('latitude', ''),
            "longitude": transaction_data.get('longitude', ''),
            "device_info": transaction_data.get('device_info', ''),
            "location": transaction_data.get('location', ''),
            "fingerprint_data": transaction_data.get('fingerprint_data', ''),
            "terminal_id": transaction_data.get('terminal_id', '')
        }
        
        # Call EKO API
        api_response = self.eko.initiate_cash_withdrawal(payload)
        
        # Save transaction to database
        merchant = AEPSMerchant.objects.get(user_code=self.user_code)
        
        transaction = AEPSTransaction.objects.create(
            eko_tid=api_response.get('data', {}).get('tid', ''),
            client_ref_id=client_ref_id,
            merchant=merchant,
            initiator_id=self.eko.INITIATOR_ID,
            customer_aadhaar=transaction_data['aadhaar_number'],
            customer_name=transaction_data.get('customer_name'),
            customer_mobile=transaction_data.get('customer_mobile'),
            transaction_type='cash_withdrawal',
            amount=transaction_data['amount'],
            bank_identifier=transaction_data['bank_identifier'],
            bank_name=transaction_data.get('bank_name'),
            status='initiated',
            status_code=api_response.get('response_status_id'),
            status_message=api_response.get('message'),
            response_data=api_response
        )
        
        return {
            'transaction_id': transaction.id,
            'client_ref_id': client_ref_id,
            'eko_tid': api_response.get('data', {}).get('tid', ''),
            'response': api_response
        }
    
    def initiate_balance_enquiry(self, enquiry_data):
        """Initiate balance enquiry"""
        client_ref_id = f"AEPSBE{int(time.time())}{enquiry_data['aadhaar_number'][-4:]}"
        
        payload = {
            "client_ref_id": client_ref_id,
            "aadhaar_number": enquiry_data['aadhaar_number'],
            "bank_identifier": enquiry_data['bank_identifier'],
            "latitude": enquiry_data.get('latitude', ''),
            "longitude": enquiry_data.get('longitude', ''),
            "device_info": enquiry_data.get('device_info', ''),
            "location": enquiry_data.get('location', ''),
            "fingerprint_data": enquiry_data.get('fingerprint_data', ''),
            "terminal_id": enquiry_data.get('terminal_id', '')
        }
        
        # Call EKO API
        api_response = self.eko.initiate_balance_enquiry(payload)
        
        # Save transaction to database
        merchant = AEPSMerchant.objects.get(user_code=self.user_code)
        
        transaction = AEPSTransaction.objects.create(
            eko_tid=api_response.get('data', {}).get('tid', ''),
            client_ref_id=client_ref_id,
            merchant=merchant,
            initiator_id=self.eko.INITIATOR_ID,
            customer_aadhaar=enquiry_data['aadhaar_number'],
            customer_name=enquiry_data.get('customer_name'),
            customer_mobile=enquiry_data.get('customer_mobile'),
            transaction_type='balance_enquiry',
            bank_identifier=enquiry_data['bank_identifier'],
            bank_name=enquiry_data.get('bank_name'),
            status='initiated',
            status_code=api_response.get('response_status_id'),
            status_message=api_response.get('message'),
            response_data=api_response
        )
        
        return {
            'transaction_id': transaction.id,
            'client_ref_id': client_ref_id,
            'eko_tid': api_response.get('data', {}).get('tid', ''),
            'response': api_response
        }
    
    def check_transaction_status(self, client_ref_id):
        """Check status of a transaction"""
        api_response = self.eko.check_transaction_status(client_ref_id)
        
        # Update transaction in database
        try:
            transaction = AEPSTransaction.objects.get(client_ref_id=client_ref_id)
            
            if api_response.get('response_status_id') == 0:
                data = api_response.get('data', {})
                transaction.status = 'success' if data.get('status') == 'success' else 'failed'
                transaction.bank_rrn = data.get('bank_rrn')
                transaction.bank_ref_num = data.get('bank_ref_num')
                transaction.completed_at = timezone.now()
            else:
                transaction.status = 'failed'
            
            transaction.status_message = api_response.get('message')
            transaction.response_data = api_response
            transaction.save()
            
        except AEPSTransaction.DoesNotExist:
            pass
        
        return api_response


# Create a global instance if needed
aeps_manager = AEPSManager()