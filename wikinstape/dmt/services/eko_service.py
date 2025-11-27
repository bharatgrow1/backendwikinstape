import requests
import json
import time
import base64
import hmac
import hashlib
from django.conf import settings
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)

class EkoAPIService:
    def __init__(self):
        self.base_url = "https://api.eko.in:25002/ekoicici"
        
        self.developer_key = getattr(settings, 'EKO_DEVELOPER_KEY', '753595f07a59eb5a52341538fad5a63d')
        self.access_key = getattr(settings, 'EKO_ACCESS_KEY', '854313b5-a37a-445a-8bc5-a27f4f0fe56a')
        
        self.initiator_id = getattr(settings, 'EKO_INITIATOR_ID', '9212094999')
        self.eko_user_code = getattr(settings, 'EKO_USER_CODE', '38130001')
        
        self.timeout = 30

    def generate_signature(self, concat_string=None):
        timestamp = str(int(time.time() * 1000))
        encoded_key = base64.b64encode(self.access_key.encode()).decode()

        hashed = hmac.new(encoded_key.encode(), timestamp.encode(), hashlib.sha256).digest()
        secret_key = base64.b64encode(hashed).decode()

        request_hash = None
        if concat_string:
            rh = hmac.new(encoded_key.encode(), concat_string.encode(), hashlib.sha256).digest()
            request_hash = base64.b64encode(rh).decode()

        return secret_key, timestamp, request_hash

    def get_headers(self, concat_string=None):
        secret_key, ts, request_hash = self.generate_signature(concat_string)

        headers = {
            "accept": "application/json",
            "developer_key": self.developer_key,
            "secret-key": secret_key,
            "secret-key-timestamp": ts,
            "content-type": "application/x-www-form-urlencoded"
        }

        if request_hash:
            headers["request_hash"] = request_hash

        return headers

    def make_request(self, method, endpoint, data=None, concat_string=None):
        url = f"{self.base_url}{endpoint}"
        headers = self.get_headers(concat_string)

        logger.info(f"EKO API Request: {method} {url}")
        logger.debug(f"Headers: {headers}")
        logger.debug(f"Payload: {data}")

        try:
            if method.upper() == "PUT":
                response = requests.put(url, data=data, headers=headers, timeout=self.timeout)
            elif method.upper() == "POST":
                response = requests.post(url, data=data, headers=headers, timeout=self.timeout)
            elif method.upper() == "GET":
                response = requests.get(url, params=data, headers=headers, timeout=self.timeout)
            else:
                return {"status": 1, "message": "Invalid method"}

            logger.info(f"EKO API Response Status: {response.status_code}")
            logger.debug(f"Response: {response.text}")

            try:
                return response.json()
            except json.JSONDecodeError:
                return {"status": 1, "message": "Invalid JSON response", "raw_response": response.text}

        except requests.exceptions.Timeout:
            logger.error("EKO API request timeout")
            return {"status": 1, "message": "Request timeout"}
        except requests.exceptions.ConnectionError:
            logger.error("EKO API connection error")
            return {"status": 1, "message": "Connection error"}
        except Exception as e:
            logger.error(f"EKO API request error: {str(e)}")
            return {"status": 1, "message": str(e)}

    # Sender Profile Methods
    def get_sender_profile(self, customer_mobile):
        """GET SENDER PROFILE - FINO DMT"""
        endpoint = f"/v3/customer/profile/{customer_mobile}/dmt-fino"
        
        params = {
            "initiator_id": self.initiator_id,
            "user_code": self.eko_user_code
        }

        return self.make_request("GET", endpoint, data=params)

    # KYC Methods
    def customer_ekyc_biometric(self, customer_id, aadhar, piddata):
        """DMT FINO BIOMETRIC KYC"""
        endpoint = f"/v3/customer/account/{customer_id}/dmt-fino/ekyc"

        payload = {
            "initiator_id": self.initiator_id,
            "user_code": self.eko_user_code,
            "aadhar": aadhar,
            "piddata": piddata
        }

        return self.make_request("POST", endpoint, data=payload)

    def verify_ekyc_otp(self, customer_id, otp, otp_ref_id, kyc_request_id):
        """Validate Customer eKYC OTP"""
        endpoint = f"/v3/customer/account/{customer_id}/dmt-fino/otp/verify"

        payload = {
            "initiator_id": self.initiator_id,
            "user_code": self.eko_user_code,
            "otp": otp,
            "otp_ref_id": otp_ref_id,
            "kyc_request_id": kyc_request_id
        }

        return self.make_request("POST", endpoint, data=payload)

    # Recipient Methods
    def add_recipient(self, customer_id, recipient_name, recipient_mobile, account, ifsc, bank_id, recipient_type=3, account_type=1):
        """Add Recipient"""
        endpoint = f"/v3/customer/payment/dmt-fino/sender/{customer_id}/recipient1"

        payload = {
            "initiator_id": self.initiator_id,
            "user_code": self.eko_user_code,
            "recipient_name": recipient_name,
            "recipient_mobile": recipient_mobile,
            "recipient_type": recipient_type,
            "account": account,
            "ifsc": ifsc,
            "bank_id": bank_id,
            "account_type": account_type
        }

        return self.make_request("POST", endpoint, data=payload)

    def get_recipient_list(self, customer_id):
        """Get Recipient List"""
        endpoint = f"/v3/customer/payment/dmt-fino/sender/{customer_id}/recipients"

        params = {
            "initiator_id": self.initiator_id,
            "user_code": self.eko_user_code,
        }

        return self.make_request("GET", endpoint, data=params)

    # Transaction Methods
    def send_transaction_otp(self, customer_id, recipient_id, amount):
        """Send Transaction OTP"""
        endpoint = f"/v3/customer/payment/dmt-fino/otp"

        payload = {
            "initiator_id": self.initiator_id,
            "user_code": self.eko_user_code,
            "recipient_id": recipient_id,
            "amount": amount,
            "customer_id": customer_id
        }

        return self.make_request("POST", endpoint, data=payload)

    def initiate_transaction(self, customer_id, recipient_id, amount, otp, otp_ref_id, latlong="26.8467,80.9462", recipient_id_type="1", currency="INR", state="1"):
        """Initiate Transaction"""
        endpoint = f"/v3/customer/payment/dmt-fino"

        from datetime import datetime
        client_ref_id = f"TXN{int(time.time())}"

        payload = {
            "initiator_id": self.initiator_id,
            "user_code": self.eko_user_code,
            "recipient_id": recipient_id,
            "recipient_id_type": recipient_id_type,
            "amount": amount,
            "currency": currency,
            "timestamp": datetime.now().isoformat(),
            "customer_id": customer_id,
            "channel": 2,
            "latlong": latlong,
            "state": state,
            "client_ref_id": client_ref_id,
            "otp": otp,
            "otp_ref_id": otp_ref_id
        }

        return self.make_request("POST", endpoint, data=payload)

    def check_api_status(self):
        """Check if EKO API is accessible"""
        try:
            response = self.get_sender_profile("9170475552")
            return response.get('status', 1) == 0
        except Exception as e:
            logger.error(f"EKO API status check failed: {str(e)}")
            return False

eko_service = EkoAPIService()