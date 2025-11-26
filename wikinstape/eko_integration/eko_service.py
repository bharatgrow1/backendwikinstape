import base64
import hmac
import hashlib
import time
import json
import requests
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class EkoAPIService:
    def __init__(self, production=True):
        if production:
            self.base_url = settings.EKO_PRODUCTION_CONFIG['BASE_URL']
            self.developer_key = settings.EKO_PRODUCTION_CONFIG['DEVELOPER_KEY']
            self.secret_key = settings.EKO_PRODUCTION_CONFIG['SECRET_KEY']
            self.initiator_id = settings.EKO_PRODUCTION_CONFIG['INITIATOR_ID']
            self.EKO_USER_CODE = settings.EKO_PRODUCTION_CONFIG['USER_CODE']
        else:
            self.base_url = "https://staging.eko.in:25004"
            self.developer_key = "becbbce45f79c6f5109f848acd540567"
            self.secret_key = "854313b5-a37a-445a-8bc5-a27f4f0fe56a"
            self.initiator_id = "9962981729"
            self.EKO_USER_CODE = "20810200"
    
    def generate_signature(self, concat_string=None):
        """Generate Eko API signature for production"""
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
        """Get headers for V2 APIs - Production"""
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
        """Generic request method for production"""
        url = f"{self.base_url}{endpoint}"
        headers = self.get_headers_v2(concat_string)
        
        try:
            logger.info(f"Eko API Request: {method} {endpoint}")
            
            if method.upper() == 'GET':
                response = requests.get(url, params=data, headers=headers, timeout=30)
            elif method.upper() == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=30)
            elif method.upper() == 'PUT':
                response = requests.put(url, json=data, headers=headers, timeout=30)
            else:
                return {'status': 1, 'message': f'Unsupported method: {method}'}
            
            logger.info(f"Eko API Response Status: {response.status_code}")
            
            try:
                response_data = response.json()
                
                if response_data.get('status') == 0:
                    logger.info(f"Eko API Success: {endpoint}")
                else:
                    logger.error(f"Eko API Error: {response_data.get('message')}")
                
                return response_data
            except json.JSONDecodeError:
                logger.error(f"Eko API JSON Decode Error: {response.text}")
                return {
                    'status': 1, 
                    'message': 'Invalid JSON response from Eko API',
                    'raw_response': response.text
                }
                
        except requests.exceptions.Timeout:
            logger.error(f"Eko API Timeout: {endpoint}")
            return {'status': 1, 'message': 'Request timeout'}
        except requests.exceptions.ConnectionError:
            logger.error(f"Eko API Connection Error: {endpoint}")
            return {'status': 1, 'message': 'Connection error'}
        except requests.exceptions.RequestException as e:
            logger.error(f"Eko API Request Error: {str(e)}")
            return {'status': 1, 'message': f'Request failed: {str(e)}'}
    
    def check_balance(self):
        """Check balance in production"""
        endpoint = f"/ekoapi/v2/customers/mobile_number:{self.initiator_id}/balance"
        
        params = {
            'initiator_id': self.initiator_id,
            'user_code': self.EKO_USER_CODE
        }
        
        timestamp = str(int(time.time() * 1000))
        concat_string = timestamp
        
        return self.make_request('GET', endpoint, params, concat_string)