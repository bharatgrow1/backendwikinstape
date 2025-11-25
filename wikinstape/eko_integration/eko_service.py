import requests
import base64
import hmac
import hashlib
import time
import json
from django.conf import settings

class EkoAPIService:
    def __init__(self):
        self.base_url = "https://api.eko.in:25002/ekoicici/"
        self.developer_key = "753595f07a59eb5a52341538fad5a63d"
        self.secret_key = "854313b5-a37a-445a-8bc5-a27f4f0fe56a"
        self.initiator_id = "9212094999"
        self.EKO_USER_CODE = "38130001"
        self.use_mock = True
    
    def generate_signature(self):
        """Generate Eko API signature"""
        timestamp = str(int(time.time() * 1000))
        encoded_key = base64.b64encode(self.secret_key.encode()).decode()
        signature = hmac.new(
            encoded_key.encode(), 
            timestamp.encode(), 
            hashlib.sha256
        ).digest()
        secret_key = base64.b64encode(signature).decode()
        
        return secret_key, timestamp
    
    def get_headers(self):
        secret_key, timestamp = self.generate_signature()
        return {
            'developer_key': self.developer_key,
            'secret-key': secret_key,
            'secret-key-timestamp': timestamp,
            'Content-Type': 'application/x-www-form-urlencoded'
        }
    
    def onboard_user(self, user_data):
        """Onboard user to Eko platform"""
        url = f"{self.base_url}/ekoapi/v1/user/onboard"
        
        # Prepare address
        address_data = {
            "line": user_data.get('address', ''),
            "city": user_data.get('city', ''),
            "state": user_data.get('state', ''),
            "pincode": user_data.get('pincode', ''),
            "district": user_data.get('city', ''),
            "area": user_data.get('landmark', '')
        }
        
        data = {
            'initiator_id': self.initiator_id,
            'pan_number': user_data.get('pan_number', ''),
            'mobile': user_data.get('phone_number', ''),
            'first_name': user_data.get('first_name', ''),
            'last_name': user_data.get('last_name', ''),
            'email': user_data.get('email', ''),
            'residence_address': json.dumps(address_data),
            'dob': user_data.get('date_of_birth', '').strftime('%Y-%m-%d') if user_data.get('date_of_birth') else '',
            'shop_name': user_data.get('business_name', f"{user_data.get('first_name', '')} Store")
        }
        
        try:
            response = requests.put(url, data=data, headers=self.get_headers())
            return response.json()
        except Exception as e:
            return {'status': 1, 'message': str(e)}
    
    def get_services(self):
        """Get available Eko services"""
        url = f"{self.base_url}/ekoapi/v1/user/services"
        params = {'initiator_id': self.initiator_id}
        
        try:
            response = requests.get(url, params=params, headers=self.get_headers())
            return response.json()
        except Exception as e:
            return {'status': 1, 'message': str(e)}
    
    def activate_service(self, user_code, service_code):
        """Activate service for user"""
        url = f"{self.base_url}/ekoapi/v1/user/service/activate"
        
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