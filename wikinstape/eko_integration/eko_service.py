import requests
import base64
import hmac
import hashlib
import time
import json
from django.conf import settings

class EkoPrepaidRechargeService:
    def __init__(self):
        self.base_url = "https://api.eko.in:25002/ekoicici"
        self.developer_key = "753595f07a59eb5a52341538fad5a63d"
        self.secret_key = "854313b5-a37a-445a-8bc5-a27f4f0fe56a"
        self.initiator_id = "9212094999"
        self.EKO_USER_CODE = "38130001"
    
    def generate_signature(self, concat_string=None):
        """Generate Eko API signature"""
        timestamp = str(int(time.time() * 1000))
        
        encoded_key = base64.b64encode(self.secret_key.encode()).decode()
        secret_key_hmac = hmac.new(
            encoded_key.encode(), 
            timestamp.encode(), 
            hashlib.sha256
        ).digest()
        secret_key = base64.b64encode(secret_key_hmac).decode()
        
        request_hash = None
        if concat_string:
            request_hash_hmac = hmac.new(
                encoded_key.encode(), 
                concat_string.encode(), 
                hashlib.sha256
            ).digest()
            request_hash = base64.b64encode(request_hash_hmac).decode()
        
        return secret_key, timestamp, request_hash
    
    def get_headers(self, concat_string=None):
        """Get headers for APIs"""
        secret_key, timestamp, request_hash = self.generate_signature(concat_string)
        
        headers = {
            'developer_key': self.developer_key,
            'secret-key': secret_key,
            'secret-key-timestamp': timestamp,
            'Content-Type': 'application/json'
        }
        
        if request_hash:
            headers['request_hash'] = request_hash
            
        return headers
    
    def make_request(self, method, endpoint, data=None, concat_string=None):
        """Generic request method"""
        url = f"{self.base_url}{endpoint}"
        headers = self.get_headers(concat_string)
        
        try:
            print(f"🔵 API Request: {method} {url}")
            print(f"🔵 Headers: {headers}")
            print(f"🔵 Payload: {data}")
            
            if method.upper() == 'GET':
                response = requests.get(url, params=data, headers=headers, timeout=30)
            elif method.upper() == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=30)
            elif method.upper() == 'PUT':
                response = requests.put(url, json=data, headers=headers, timeout=30)
            else:
                return {'status': 1, 'message': f'Unsupported method: {method}'}
            
            print(f"🟢 Response Status: {response.status_code}")
            print(f"🟢 Response Text: {response.text}")
            
            try:
                return response.json()
            except json.JSONDecodeError:
                return {
                    'status': 1, 
                    'message': f'Invalid JSON response: {response.text}',
                    'raw_response': response.text
                }
                
        except requests.exceptions.RequestException as e:
            return {'status': 1, 'message': f'Request failed: {str(e)}'}

    def prepaid_recharge(self, mobile, amount, operator_id, circle='DELHI'):
        """PREPAID RECHARGE - Correct endpoint and parameters"""
        
        # Generate unique reference
        client_ref_id = f"PR{int(time.time())}"
        
        # For prepaid recharge, we need different endpoint and parameters
        timestamp = str(int(time.time() * 1000))
        amount_str = str(float(amount))
        concat_string = f"{timestamp}{mobile}{amount_str}{self.EKO_USER_CODE}"
        
        # CORRECT ENDPOINT FOR PREPAID RECHARGE
        endpoint = "/v2/billpayments/recharge"
        
        # CORRECT PAYLOAD FOR PREPAID RECHARGE
        payload = {
            "initiator_id": self.initiator_id,
            "user_code": self.EKO_USER_CODE,
            "amount": float(amount),
            "client_ref_id": client_ref_id,
            "mobile_no": mobile,
            "operator_id": operator_id,
            "circle": circle,
            "latlong": "28.6139,77.2090"
        }
        
        return self.make_request('POST', endpoint, payload, concat_string)
    
    def check_prepaid_operators(self):
        """Get prepaid operators list"""
        endpoint = "/v2/billpayments/operators"
        params = {
            'initiator_id': self.initiator_id,
            'user_code': self.EKO_USER_CODE,
            'service_type': 'prepaid'
        }
        
        return self.make_request('GET', endpoint, params)