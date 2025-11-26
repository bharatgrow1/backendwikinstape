import requests
import base64
import hmac
import hashlib
import time
import json
from urllib.parse import urlencode
from django.conf import settings

class EkoAPIService:
    def __init__(self):
        self.base_url = "https://api.eko.in:25002/ekoicici"
        self.developer_key = "753595f07a59eb5a52341538fad5a63d"
        self.secret_key = "854313b5-a37a-445a-8bc5-a27f4f0fe56a"
        self.initiator_id = "9212094999"
        self.EKO_USER_CODE = "38130001"
        self.use_mock = False
    
    def generate_signature_v1(self, data_string=None):
        """Generate signature for V1 APIs (form-data)"""
        timestamp = str(int(time.time() * 1000))
        
        secret_key_hmac = hmac.new(
            self.secret_key.encode(),
            timestamp.encode(),
            hashlib.sha256
        ).digest()
        secret_key = base64.b64encode(secret_key_hmac).decode()
        
        return secret_key, timestamp
    
    def get_headers_v1(self):
        """Headers for V1 APIs (form-data)"""
        secret_key, timestamp = self.generate_signature_v1()
        return {
            'developer_key': self.developer_key,
            'secret-key': secret_key,
            'secret-key-timestamp': timestamp,
            'Content-Type': 'application/x-www-form-urlencoded'
        }
    
    def make_request_v1(self, method, endpoint, data=None):
        """Make request for V1 APIs (form-data)"""
        url = f"{self.base_url}{endpoint}"
        headers = self.get_headers_v1()
        
        try:
            if method.upper() == 'POST':
                response = requests.post(url, data=data, headers=headers, timeout=30)
            elif method.upper() == 'GET':
                response = requests.get(url, params=data, headers=headers, timeout=30)
            elif method.upper() == 'PUT':
                response = requests.put(url, data=data, headers=headers, timeout=30)
            else:
                return {'status': 1, 'message': f'Unsupported method: {method}'}
            
            print(f"🔧 API Request: {method} {url}")
            print(f"🔧 Headers: {headers}")
            print(f"🔧 Payload: {data}")
            print(f"🔧 Response Status: {response.status_code}")
            print(f"🔧 Response Text: {response.text}")
            
            try:
                return response.json()
            except json.JSONDecodeError:
                return {
                    'status': 1, 
                    'message': f'Invalid JSON response: {response.text}',
                    'raw_response': response.text
                }
                
        except requests.exceptions.RequestException as e:
            print(f"🔧 Request Error: {str(e)}")
            return {'status': 1, 'message': f'Request failed: {str(e)}'}
    
    def make_request(self, method, endpoint, data=None, concat_string=None):
        """Generic request method - for recharge service compatibility"""
        # Recharge service के लिए temporary solution
        return self.make_request_v1(method, endpoint, data)
    
    def onboard_user(self, user_data):
        """Onboard user to Eko platform - CORRECTED as per documentation"""
        endpoint = "/ekoapi/v1/user/onboard"
        
        # Form-data format में भेजना है
        data = {
            'initiator_id': self.initiator_id,
            'pan_number': user_data.get('pan_number', 'ABCDE1234F'),
            'mobile': user_data.get('phone_number', ''),
            'first_name': user_data.get('first_name', '')[:20],
            'middle_name': user_data.get('middle_name', ''),
            'last_name': user_data.get('last_name', '')[:20],
            'email': user_data.get('email', 'test@example.com'),
            'residence_address': json.dumps({
                "line1": user_data.get('address', 'Test Address')[:35],
                "city": user_data.get('city', 'Delhi')[:20],
                "state": user_data.get('state', 'Delhi')[:20],
                "pincode": user_data.get('pincode', '110001'),
                "country": "IND"
            }),
            'dob': user_data.get('date_of_birth', '1990-01-01').strftime('%Y-%m-%d'),
            'shop_name': user_data.get('business_name', f"{user_data.get('first_name', '')} Store")[:30]
        }
        
        data = {k: v for k, v in data.items() if v}
        
        return self.make_request_v1('PUT', endpoint, data)