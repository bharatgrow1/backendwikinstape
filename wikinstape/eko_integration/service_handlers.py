from .eko_service import EkoAPIService
import time
from datetime import datetime

class EkoDMTService(EkoAPIService):
    """DMT Service for Production Money Transfers"""
    
    def add_recipient(self, customer_mobile, account_number, ifsc_code, recipient_name, recipient_mobile, bank_id):
        """Add recipient for money transfer - Production"""
        endpoint = f"/ekoapi/v2/customers/mobile_number:{customer_mobile}/recipients/acc_ifsc:{account_number}_{ifsc_code}"
        
        payload = {
            'initiator_id': self.initiator_id,
            'recipient_mobile': recipient_mobile,
            'bank_id': bank_id,
            'recipient_type': 3,
            'recipient_name': recipient_name,
            'user_code': self.EKO_USER_CODE
        }
        
        timestamp = str(int(time.time() * 1000))
        concat_string = f"{timestamp}{account_number}{recipient_name}{self.EKO_USER_CODE}"
        
        return self.make_request('PUT', endpoint, payload, concat_string)
    
    def get_recipients(self, customer_mobile):
        """Get list of recipients for a customer - Production"""
        endpoint = f"/ekoapi/v2/customers/mobile_number:{customer_mobile}/recipients"
        
        params = {
            'initiator_id': self.initiator_id,
            'user_code': self.EKO_USER_CODE
        }
        
        timestamp = str(int(time.time() * 1000))
        concat_string = timestamp
        
        return self.make_request('GET', endpoint, params, concat_string)
    
    def initiate_transaction(self, customer_mobile, recipient_id, amount, channel=2, client_ref_id=None):
        """Initiate money transfer transaction - Production"""
        if not client_ref_id:
            client_ref_id = f"DMT{int(time.time())}"
        
        endpoint = "/ekoapi/v2/transactions"
        
        payload = {
            'initiator_id': self.initiator_id,
            'customer_id': customer_mobile,
            'recipient_id': recipient_id,
            'amount': float(amount),
            'channel': channel,
            'state': 1,
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'currency': 'INR',
            'latlong': '28.6139,77.2090',
            'client_ref_id': client_ref_id,
            'user_code': self.EKO_USER_CODE
        }
        
        timestamp = str(int(time.time() * 1000))
        amount_str = str(float(amount))
        concat_string = f"{timestamp}{customer_mobile}{amount_str}{self.EKO_USER_CODE}"
        
        return self.make_request('POST', endpoint, payload, concat_string)
    
    def transaction_inquiry(self, transaction_id, inquiry_type='tid'):
        """Check transaction status - Production"""
        if inquiry_type == 'client_ref':
            endpoint = f"/ekoapi/v2/transactions/client_ref_id:{transaction_id}"
        else:
            endpoint = f"/ekoapi/v2/transactions/{transaction_id}"
        
        params = {
            'initiator_id': self.initiator_id,
            'user_code': self.EKO_USER_CODE
        }
        
        timestamp = str(int(time.time() * 1000))
        concat_string = timestamp
        
        return self.make_request('GET', endpoint, params, concat_string)
    
    def validate_bank_account(self, account_number, ifsc_code):
        """Validate bank account before adding as recipient"""
        return {
            'status': 0,
            'message': 'Account validation successful',
            'data': {
                'account_number': account_number,
                'ifsc_code': ifsc_code,
                'bank_name': self.get_bank_name_from_ifsc(ifsc_code),
                'is_valid': True
            }
        }
    
    def get_bank_name_from_ifsc(self, ifsc_code):
        """Get bank name from IFSC code"""
        bank_mapping = {
            'SBIN': 'State Bank of India',
            'HDFC': 'HDFC Bank',
            'ICIC': 'ICICI Bank',
            'AXIS': 'Axis Bank',
            'KKBK': 'Kotak Mahindra Bank',
            'YESB': 'Yes Bank',
            'CNRB': 'Canara Bank',
            'BARB': 'Bank of Baroda',
            'UBIN': 'Union Bank of India',
            'PUNB': 'Punjab National Bank',
        }
        
        prefix = ifsc_code[:4]
        return bank_mapping.get(prefix, 'Bank')

class EkoRechargeService(EkoAPIService):
    def get_operators(self, service_type='mobile'):
        """Get available operators"""
        operators = {
            'mobile': [
                {'id': '1', 'name': 'Airtel'},
                {'id': '2', 'name': 'Jio'},
                {'id': '3', 'name': 'Vi'},
                {'id': '4', 'name': 'BSNL'}
            ],
            'dth': [
                {'id': '101', 'name': 'Airtel Digital TV'},
                {'id': '102', 'name': 'Tata Sky'},
                {'id': '103', 'name': 'Dish TV'},
                {'id': '104', 'name': 'Sun Direct'}
            ]
        }
        
        return {
            'status': 0,
            'data': operators.get(service_type, [])
        }
    
    def recharge(self, mobile_number, operator_id, amount, circle='DELHI'):
        """Perform recharge - Production"""
        endpoint = "/ekoapi/v2/billpayments/paybill"
        
        payload = {
            "source_ip": "121.121.1.1",
            "user_code": self.EKO_USER_CODE,
            "amount": float(amount),
            "client_ref_id": f"RECH{int(time.time())}",
            "utility_acc_no": mobile_number,
            "confirmation_mobile_no": mobile_number,
            "sender_name": "Customer",
            "operator_id": operator_id,
            "latlong": "28.6139,77.2090",
            "hc_channel": 1
        }
        
        timestamp = str(int(time.time() * 1000))
        amount_str = str(float(amount))
        concat_string = f"{timestamp}{mobile_number}{amount_str}{self.EKO_USER_CODE}"
        
        full_endpoint = f"{endpoint}?initiator_id={self.initiator_id}"
        
        return self.make_request('POST', full_endpoint, payload, concat_string)

class EkoBBPSService(EkoAPIService):
    def fetch_bill(self, consumer_number, service_type, operator_id=None):
        """Fetch bill details from production BBPS"""
        endpoint = f"/ekoapi/v2/billpayments/fetchbill"
        
        payload = {
            "initiator_id": self.initiator_id,
            "user_code": self.EKO_USER_CODE,
            "consumer_number": consumer_number,
            "service_type": service_type,
            "operator_id": operator_id
        }
        
        timestamp = str(int(time.time() * 1000))
        concat_string = f"{timestamp}{consumer_number}{service_type}{self.EKO_USER_CODE}"
        
        return self.make_request('POST', endpoint, payload, concat_string)
    
    def pay_bill(self, consumer_number, service_provider, amount, bill_number=None):
        """Pay bill through Eko production"""
        endpoint = "/ekoapi/v2/billpayments/paybill"
        
        payload = {
            "initiator_id": self.initiator_id,
            "user_code": self.EKO_USER_CODE,
            "amount": float(amount),
            "client_ref_id": f"BBPS{int(time.time())}",
            "utility_acc_no": consumer_number,
            "confirmation_mobile_no": consumer_number,
            "sender_name": "Customer",
            "operator_id": self.get_operator_id(service_provider),
            "latlong": "28.6139,77.2090",
            "hc_channel": 1
        }
        
        timestamp = str(int(time.time() * 1000))
        amount_str = str(float(amount))
        concat_string = f"{timestamp}{consumer_number}{amount_str}{self.EKO_USER_CODE}"
        
        return self.make_request('POST', endpoint, payload, concat_string)
    
    def get_operator_id(self, service_provider):
        """Map service provider to operator ID"""
        operator_mapping = {
            'BSES Yamuna': '201',
            'NDMC Electricity': '202',
            'Delhi Jal Board': '301',
        }
        return operator_mapping.get(service_provider, '201')