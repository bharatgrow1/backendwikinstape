import requests
import base64
import hmac
import hashlib
import time
import json
from django.conf import settings

class EkoAPIService:
    def __init__(self):
        # V1 APIs ke liye alag base URL (Money Transfer)
        self.v1_base_url = "https://api.eko.in:25002/ekoicici"
        # V2 APIs ke liye alag base URL (Recharge)
        self.v2_base_url = "https://api.eko.in:25002/ekoicici"
        
        self.developer_key = "753595f07a59eb5a52341538fad5a63d"
        self.secret_key = "854313b5-a37a-445a-8bc5-a27f4f0fe56a"
        self.initiator_id = "9212094999"
        self.EKO_USER_CODE = "38130001"
        self.use_mock = False
    
    def generate_signature_v1(self):
        """Generate signature for V1 APIs (Money Transfer)"""
        timestamp = str(int(time.time() * 1000))
        
        # V1 APIs ke liye simple signature
        encoded_key = base64.b64encode(self.secret_key.encode()).decode()
        secret_key_hmac = hmac.new(
            encoded_key.encode(), 
            timestamp.encode(), 
            hashlib.sha256
        ).digest()
        secret_key = base64.b64encode(secret_key_hmac).decode()
        
        return secret_key, timestamp
    
    def generate_signature_v2(self, concat_string=None):
        """Generate signature for V2 APIs (Recharge)"""
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
    
    def get_headers_v1(self):
        """Headers for V1 APIs (Money Transfer)"""
        secret_key, timestamp = self.generate_signature_v1()
        
        return {
            'developer_key': self.developer_key,
            'secret-key': secret_key,
            'secret-key-timestamp': timestamp,
            'Content-Type': 'application/x-www-form-urlencoded'
        }
    
    def get_headers_v2(self, concat_string=None):
        """Headers for V2 APIs (Recharge)"""
        secret_key, timestamp, request_hash = self.generate_signature_v2(concat_string)
        
        headers = {
            'developer_key': self.developer_key,
            'secret-key': secret_key,
            'secret-key-timestamp': timestamp,
            'Content-Type': 'application/json'
        }
        
        if request_hash:
            headers['request_hash'] = request_hash
            
        return headers
    
    def make_request_v1(self, method, endpoint, data=None):
        """Request method for V1 APIs - MONEY TRANSFER"""
        # V1 APIs ke liye alag base URL
        url = f"https://api.eko.in:25002/ekoapi/v1{endpoint}"
        headers = self.get_headers_v1()
        
        try:
            print(f"V1 API Request: {method} {url}")
            print(f"Headers: {headers}")
            print(f"Form Data: {data}")
            
            if method.upper() == 'POST':
                response = requests.post(url, data=data, headers=headers, timeout=30)
            elif method.upper() == 'GET':
                response = requests.get(url, params=data, headers=headers, timeout=30)
            elif method.upper() == 'PUT':
                response = requests.put(url, data=data, headers=headers, timeout=30)
            else:
                return {'status': 1, 'message': f'Unsupported method: {method}'}
            
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
    
    def make_request_v2(self, method, endpoint, data=None, concat_string=None):
        """Request method for V2 APIs - RECHARGE"""
        # V2 APIs ke liye alag base URL
        url = f"{self.v2_base_url}{endpoint}"
        headers = self.get_headers_v2(concat_string)
        
        try:
            print(f"V2 API Request: {method} {url}")
            print(f"Headers: {headers}")
            print(f"Payload: {data}")
            
            if method.upper() == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=30)
            elif method.upper() == 'GET':
                response = requests.get(url, params=data, headers=headers, timeout=30)
            elif method.upper() == 'PUT':
                response = requests.put(url, json=data, headers=headers, timeout=30)
            else:
                return {'status': 1, 'message': f'Unsupported method: {method}'}
            
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