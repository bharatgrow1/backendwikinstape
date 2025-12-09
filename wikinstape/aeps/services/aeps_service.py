import time
import base64
import hmac
import hashlib
import json
import requests
from django.conf import settings

class EkoAEPSService:
    BASE_URL = "https://api.eko.in:25002/ekoicici"
    DEVELOPER_KEY = "753595f07a59eb5a52341538fad5a63d"
    ACCESS_KEY = "854313b5-a37a-445a-8bc5-a27f4f0fe56a"
    INITIATOR_ID = "9212094999"
    
    def __init__(self, user_code=None):
        self.user_code = user_code
    
    def generate_secret(self):
        """Generate secret key and timestamp for authentication"""
        ts = str(int(time.time() * 1000))
        encoded = base64.b64encode(self.ACCESS_KEY.encode()).decode()
        hashed = hmac.new(encoded.encode(), ts.encode(), hashlib.sha256).digest()
        secret = base64.b64encode(hashed).decode()
        return secret, ts
    
    def make_request(self, method, endpoint, data=None, form_data=False):
        """Make API request to EKO"""
        secret, timestamp = self.generate_secret()
        
        headers = {
            "developer_key": self.DEVELOPER_KEY,
            "secret-key": secret,
            "secret-key-timestamp": timestamp,
            "accept": "application/json",
        }
        
        if form_data:
            headers["content-type"] = "application/x-www-form-urlencoded"
        else:
            headers["content-type"] = "application/json"
        
        url = self.BASE_URL + endpoint
        
        try:
            if method == "PUT":
                response = requests.put(url, headers=headers, data=data)
            elif method == "POST":
                response = requests.post(url, headers=headers, data=data)
            elif method == "GET":
                response = requests.get(url, headers=headers, params=data)
            else:
                raise ValueError(f"Invalid method: {method}")
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            return {
                "response_status_id": -1,
                "message": str(e),
                "status": 0
            }
    
    def onboard_merchant(self, merchant_data):
        """Onboard a new merchant for AEPS"""
        endpoint = "/v1/user/onboard"
        
        # Prepare form data
        data = {
            "initiator_id": self.INITIATOR_ID,
            "pan_number": merchant_data['pan_number'],
            "mobile": merchant_data['mobile'],
            "first_name": merchant_data['first_name'],
            "middle_name": merchant_data.get('middle_name', ''),
            "last_name": merchant_data.get('last_name', ''),
            "email": merchant_data['email'],
            "residence_address": json.dumps({
                "line": merchant_data['address_line'],
                "city": merchant_data['city'],
                "state": merchant_data['state'],
                "pincode": merchant_data['pincode'],
                "district": merchant_data.get('district', ''),
                "area": merchant_data.get('area', '')
            }),
            "dob": merchant_data['dob'],
            "shop_name": merchant_data['shop_name']
        }
        
        # Convert to form-urlencoded format
        form_data = "&".join([f"{k}={v}" for k, v in data.items()])
        return self.make_request("PUT", endpoint, form_data, form_data=True)
    
    def initiate_cash_withdrawal(self, transaction_data):
        """Initiate cash withdrawal transaction"""
        endpoint = f"/aeps/user_code:{self.user_code}/cash_withdrawal"
        
        payload = {
            "initiator_id": self.INITIATOR_ID,
            "client_ref_id": transaction_data['client_ref_id'],
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
        
        return self.make_request("POST", endpoint, json.dumps(payload))
    
    def initiate_balance_enquiry(self, enquiry_data):
        """Initiate balance enquiry"""
        endpoint = f"/aeps/user_code:{self.user_code}/balance_enquiry"
        
        payload = {
            "initiator_id": self.INITIATOR_ID,
            "client_ref_id": enquiry_data['client_ref_id'],
            "aadhaar_number": enquiry_data['aadhaar_number'],
            "bank_identifier": enquiry_data['bank_identifier'],
            "latitude": enquiry_data.get('latitude', ''),
            "longitude": enquiry_data.get('longitude', ''),
            "device_info": enquiry_data.get('device_info', ''),
            "location": enquiry_data.get('location', ''),
            "fingerprint_data": enquiry_data.get('fingerprint_data', ''),
            "terminal_id": enquiry_data.get('terminal_id', '')
        }
        
        return self.make_request("POST", endpoint, json.dumps(payload))
    
    def initiate_mini_statement(self, statement_data):
        """Initiate mini statement request"""
        endpoint = f"/aeps/user_code:{self.user_code}/mini_statement"
        
        payload = {
            "initiator_id": self.INITIATOR_ID,
            "client_ref_id": statement_data['client_ref_id'],
            "aadhaar_number": statement_data['aadhaar_number'],
            "bank_identifier": statement_data['bank_identifier'],
            "latitude": statement_data.get('latitude', ''),
            "longitude": statement_data.get('longitude', ''),
            "device_info": statement_data.get('device_info', ''),
            "location": statement_data.get('location', ''),
            "fingerprint_data": statement_data.get('fingerprint_data', ''),
            "terminal_id": statement_data.get('terminal_id', '')
        }
        
        return self.make_request("POST", endpoint, json.dumps(payload))
    
    def check_transaction_status(self, client_ref_id):
        """Check transaction status"""
        endpoint = f"/transaction/user_code:{self.user_code}/client_ref_id:{client_ref_id}/status"
        
        payload = {
            "initiator_id": self.INITIATOR_ID
        }
        
        return self.make_request("GET", endpoint, payload)