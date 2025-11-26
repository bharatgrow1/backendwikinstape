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
    
    def generate_signature(self, concat_string=None):
        """Generate Eko API signature - EXACTLY like Ruby code"""
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
            if method.upper() == 'GET':
                response = requests.get(url, params=data, headers=headers, timeout=30)
            elif method.upper() == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=30)
            elif method.upper() == 'PUT':
                response = requests.put(url, json=data, headers=headers, timeout=30)
            else:
                return {'status': 1, 'message': f'Unsupported method: {method}'}
            
            print(f"API Request: {method} {url}")
            print(f"Headers: {headers}")
            print(f"Payload: {data}")
            print(f"Response Status: {response.status_code}")
            print(f"Response Text: {response.text}")
            
            try:
                return response.json()
            except json.JSONDecodeError:
                return {
                    'status': 1, 
                    'message': f'Invalid JSON response: {response.text}',
                    'raw_response': response.text
                }
                
        except requests.exceptions.RequestException as e:
            print(f"Request Error: {str(e)}")
            return {'status': 1, 'message': f'Request failed: {str(e)}'}
    
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
    
    
    def onboard_user(self, user_data):
        """Onboard user to Eko platform - Fixed version"""
        endpoint = "/v2/users/onboard"
        
        address_data = {
            "line1": user_data.get('address', '')[:35],
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