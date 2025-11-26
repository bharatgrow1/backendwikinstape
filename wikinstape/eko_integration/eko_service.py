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
    
    def generate_signature(self, concat_string=None):
        """Generate Eko API signature - EXACTLY like Ruby code"""
        timestamp = str(int(time.time() * 1000))
        
        # Ruby: encoded_key = Base64.strict_encode64(access_key)
        encoded_key = base64.b64encode(self.secret_key.encode()).decode()
        
        # Ruby: secret_key_hmac = OpenSSL::HMAC.digest("SHA256", encoded_key, timestamp)
        secret_key_hmac = hmac.new(
            encoded_key.encode(), 
            timestamp.encode(), 
            hashlib.sha256
        ).digest()
        secret_key = base64.b64encode(secret_key_hmac).decode()
        
        request_hash = None
        if concat_string:
            # Ruby: request_hash_hmac = OpenSSL::HMAC.digest("SHA256", encoded_key, concat_string)
            request_hash_hmac = hmac.new(
                encoded_key.encode(), 
                concat_string.encode(), 
                hashlib.sha256
            ).digest()
            request_hash = base64.b64encode(request_hash_hmac).decode()
        
        return secret_key, timestamp, request_hash
    
    def get_headers_v2(self, concat_string=None):
        """Get headers for V2 APIs - EXACTLY like Ruby"""
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
        """Generic request method with proper error handling"""
        url = f"{self.base_url}{endpoint}"
        headers = self.get_headers_v2(concat_string)
        
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
                response_data = response.json()
                print(f"🟢 Parsed JSON: {response_data}")
                return response_data
            except json.JSONDecodeError:
                print(f"🔴 JSON Parse Error: {response.text}")
                return {
                    'status': 1, 
                    'message': f'Invalid JSON response: {response.text}',
                    'raw_response': response.text
                }
                
        except requests.exceptions.RequestException as e:
            print(f"🔴 Request Error: {str(e)}")
            return {'status': 1, 'message': f'Request failed: {str(e)}'}

    # MOBILE RECHARGE METHOD - EXACTLY LIKE RUBY
    def mobile_recharge(self, mobile, amount, operator_id, client_ref_id=None):
        """Mobile recharge - EXACT Ruby implementation"""
        if not client_ref_id:
            client_ref_id = f"RECH{int(time.time())}"
        
        # Generate concat_string exactly like Ruby
        timestamp = str(int(time.time() * 1000))
        amount_str = str(float(amount))
        concat_string = f"{timestamp}{mobile}{amount_str}{self.EKO_USER_CODE}"
        
        endpoint = "/v2/billpayments/paybill"
        
        # Payload exactly like Ruby
        payload = {
            "source_ip": "121.121.1.1",
            "user_code": self.EKO_USER_CODE,
            "amount": float(amount),
            "client_ref_id": client_ref_id,
            "utility_acc_no": mobile,
            "confirmation_mobile_no": mobile,
            "sender_name": "Customer",
            "operator_id": operator_id,
            "latlong": "28.6139,77.2090",
            "hc_channel": 1
        }
        
        # URL with initiator exactly like Ruby
        full_endpoint = f"{endpoint}?initiator_id={self.initiator_id}"
        
        return self.make_request('POST', full_endpoint, payload, concat_string)
    
    def check_balance(self):
        """Check balance - Ruby code ke according"""
        endpoint = f"/v2/customers/mobile_number:{self.initiator_id}/balance"
        params = {
            'initiator_id': self.initiator_id,
            'user_code': self.EKO_USER_CODE
        }
        
        timestamp = str(int(time.time() * 1000))
        concat_string = timestamp
        
        return self.make_request('GET', endpoint, params, concat_string)