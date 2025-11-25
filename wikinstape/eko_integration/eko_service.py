import requests
import base64
import hmac
import hashlib
import time
import json
from django.conf import settings

class EkoAPIService:
    def __init__(self):
        self.base_url = "https://api.eko.in:25002/ekoicici"
        self.developer_key = "753595f07a59eb5a52341538fad5a63d"
        self.secret_key = "854313b5-a37a-445a-8bc5-a27f4f0fe56a"
        self.initiator_id = "9212094999"
        self.EKO_USER_CODE = "38130001"
        self.use_mock = False
    
    def generate_signature(self, request_data=None):
        """Generate Eko API signature - Fixed to match Ruby implementation"""
        timestamp = str(int(time.time() * 1000))
        
        # Step 1: Generate SECRET-KEY (same as Ruby)
        encoded_key = base64.b64encode(self.secret_key.encode()).decode()
        secret_key_hmac = hmac.new(
            encoded_key.encode(), 
            timestamp.encode(), 
            hashlib.sha256
        ).digest()
        secret_key = base64.b64encode(secret_key_hmac).decode()
        
        # Step 2: Generate REQUEST-HASH if request_data is provided
        request_hash = None
        if request_data:
            # Create concatenated string based on API requirements
            if 'utility_acc_no' in request_data and 'amount' in request_data:
                # For bill payments/recharge
                concat_string = f"{timestamp}{request_data['utility_acc_no']}{request_data['amount']}{self.EKO_USER_CODE}"
            elif 'account_number' in request_data and 'amount' in request_data:
                # For money transfer
                concat_string = f"{timestamp}{request_data['account_number']}{request_data['amount']}{self.EKO_USER_CODE}"
            else:
                # Default concatenation
                concat_string = timestamp
            
            request_hash_hmac = hmac.new(
                encoded_key.encode(), 
                concat_string.encode(), 
                hashlib.sha256
            ).digest()
            request_hash = base64.b64encode(request_hash_hmac).decode()
        
        return secret_key, timestamp, request_hash
    
    def get_headers(self, request_data=None):
        """Get headers with proper signature"""
        secret_key, timestamp, request_hash = self.generate_signature(request_data)
        
        headers = {
            'developer_key': self.developer_key,
            'secret-key': secret_key,
            'secret-key-timestamp': timestamp,
            'Content-Type': 'application/json'
        }
        
        if request_hash:
            headers['request_hash'] = request_hash
            
        return headers
    
    def onboard_user(self, user_data):
        """Onboard user to Eko platform - Fixed version"""
        endpoint = "/v2/users/onboard"
        
        # Prepare address
        address_data = {
            "line1": user_data.get('address', '')[:35],  # Eko has length limits
            "city": user_data.get('city', '')[:20],
            "state": user_data.get('state', '')[:20],
            "pincode": user_data.get('pincode', ''),
            "country": "IND"
        }
        
        data = {
            'initiator_id': self.initiator_id,
            'user_code': self.EKO_USER_CODE,
            'mobile': user_data.get('phone_number', ''),
            'first_name': user_data.get('first_name', '')[:20],
            'last_name': user_data.get('last_name', '')[:20],
            'email': user_data.get('email', ''),
            'address': address_data,
            'dob': user_data.get('date_of_birth', '').strftime('%d/%m/%Y') if user_data.get('date_of_birth') else '',
            'business_name': user_data.get('business_name', f"{user_data.get('first_name', '')} Store")[:30]
        }
        
        # Remove empty fields
        data = {k: v for k, v in data.items() if v}
        
        return self.make_request('PUT', endpoint, data)
    

    def get_services(self):
        """Get available Eko services"""
        url = f"{self.base_url}/ekoapi/v2/user/services"
        params = {'initiator_id': self.initiator_id}
        
        try:
            response = requests.get(url, params=params, headers=self.get_headers())
            return response.json()
        except Exception as e:
            return {'status': 1, 'message': str(e)}
    
    def activate_service(self, user_code, service_code):
        """Activate service for user"""
        url = f"{self.base_url}/ekoapi/v2/user/service/activate"
        
        data = {
            'user_code': user_code,
            'initiator_id': self.initiator_id,
            'service_code': service_code
        }
        
        try:
            response = requests.put(url, data=data, headers=self.get_headers())
            return response.json()
        except Exception as e:
            return {'status': 1, 'message': str(e)}