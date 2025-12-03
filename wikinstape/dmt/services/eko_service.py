import requests
import json
import time
import base64
import hmac
import hashlib
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class EkoAPIService:
    def __init__(self):
        self.base_url = "https://api.eko.in:25002/ekoicici"
        
        self.developer_key = "753595f07a59eb5a52341538fad5a63d"
        self.access_key = "854313b5-a37a-445a-8bc5-a27f4f0fe56a"
        self.initiator_id = "9212094999"
        self.EKO_USER_CODE = "38130001"
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
        logger.info(f"Headers: {headers}")
        logger.info(f"Payload: {data}")

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
            logger.info(f"Response: {response.text}")

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

    def onboard_user(self, user_data):
        """User Onboarding - PUT /v1/user/onboard"""
        endpoint = "/v1/user/onboard"

        residence_address_json = json.dumps(user_data["residence_address"])

        payload = {
            "initiator_id": self.initiator_id,
            "user_code": self.EKO_USER_CODE,
            "pan_number": user_data["pan_number"],
            "mobile": user_data["mobile"],
            "first_name": user_data["first_name"],
            "last_name": user_data["last_name"],
            "email": user_data["email"],
            "residence_address": residence_address_json,
            "dob": user_data["dob"],
            "shop_name": user_data["shop_name"]
        }

        return self.make_request("PUT", endpoint, payload)


    def verify_customer_identity(self, customer_mobile, otp, otp_ref_id):
        """
        Verify Customer Identity with OTP
        POST /v3/customer/{customer_mobile}/verify
        """
        endpoint = f"/v3/customer/{customer_mobile}/verify"
        
        payload = {
            "initiator_id": self.initiator_id,
            "user_code": self.EKO_USER_CODE,
            "otp": otp,
            "otp_ref_id": otp_ref_id
        }
        
        return self.make_request("POST", endpoint, payload)

    def resend_otp(self, customer_mobile):
        """
        Resend OTP for verification
        POST /v3/customer/{customer_mobile}/resend-otp
        """
        endpoint = f"/v3/customer/{customer_mobile}/resend-otp"
        
        payload = {
            "initiator_id": self.initiator_id,
            "user_code": self.EKO_USER_CODE
        }
        
        return self.make_request("POST", endpoint, payload)



    def create_customer(self, customer_data):
        """
        Create Customer for DMT
        POST /v3/customer/account/{customer_id}/dmt-fino
        """
        customer_id = customer_data.get("mobile")
        
        if not customer_id:
            return {"status": 1, "message": "Customer mobile number is required"}
        
        endpoint = f"/v3/customer/account/{customer_id}/dmt-fino"
        
        residence_address = {
            "line": customer_data.get("address_line", "India"),
            "city": customer_data.get("city", ""),
            "state": customer_data.get("state", ""),
            "pincode": customer_data.get("pincode", ""),
            "district": customer_data.get("district", ""),
            "area": customer_data.get("area", "")
        }
        
        residence_address_json = json.dumps(residence_address)
        
        payload = {
            "initiator_id": self.initiator_id,
            "name": customer_data.get("name", ""),
            "user_code": self.EKO_USER_CODE,
            "dob": customer_data.get("dob", ""),
            "residence_address": residence_address_json
        }
        
        if customer_data.get("skip_verification"):
            payload["skip_verification"] = "true" 
        
        return self.make_request("POST", endpoint, payload)
    
    

    def get_sender_profile(self, customer_mobile):
        """GET SENDER PROFILE - GET /v3/customer/profile/{customer_mobile}/dmt-fino"""
        endpoint = f"/v3/customer/profile/{customer_mobile}/dmt-fino"
        
        params = {
            "initiator_id": self.initiator_id,
            "user_code": self.EKO_USER_CODE
        }

        return self.make_request("GET", endpoint, data=params)

    def customer_ekyc_biometric(self, customer_id, aadhar, piddata):
        """DMT FINO BIOMETRIC KYC - POST /v3/customer/account/{customer_id}/dmt-fino/ekyc"""
        endpoint = f"/v3/customer/account/{customer_id}/dmt-fino/ekyc"

        payload = {
            "initiator_id": self.initiator_id,
            "user_code": self.EKO_USER_CODE,
            "aadhar": aadhar,
            "piddata": piddata
        }

        return self.make_request("POST", endpoint, data=payload)

    def verify_ekyc_otp(self, customer_id, otp, otp_ref_id, kyc_request_id):
        """Validate Customer eKYC OTP - POST /v3/customer/account/{customer_id}/dmt-fino/otp/verify"""
        endpoint = f"/v3/customer/account/{customer_id}/dmt-fino/otp/verify"

        payload = {
            "initiator_id": self.initiator_id,
            "user_code": self.EKO_USER_CODE,
            "otp": otp,
            "otp_ref_id": otp_ref_id,
            "kyc_request_id": kyc_request_id
        }

        return self.make_request("POST", endpoint, data=payload)

    def add_recipient(self, customer_id, recipient_name, recipient_mobile, account, ifsc, bank_id, recipient_type=3, account_type=1):
        """Add Recipient - POST /v3/customer/payment/dmt-fino/sender/{customer_id}/recipient1"""
        endpoint = f"/v3/customer/payment/dmt-fino/sender/{customer_id}/recipient1"

        payload = {
            "initiator_id": self.initiator_id,
            "user_code": self.EKO_USER_CODE,
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
        """Get Recipient List - GET /v3/customer/payment/dmt-fino/sender/{customer_id}/recipients"""
        endpoint = f"/v3/customer/payment/dmt-fino/sender/{customer_id}/recipients"

        params = {
            "initiator_id": self.initiator_id,
            "user_code": self.EKO_USER_CODE,
        }

        return self.make_request("GET", endpoint, data=params)

    def send_transaction_otp(self, customer_id, recipient_id, amount):
        """Send Transaction OTP - POST /v3/customer/payment/dmt-fino/otp"""
        endpoint = f"/v3/customer/payment/dmt-fino/otp"

        payload = {
            "initiator_id": self.initiator_id,
            "user_code": self.EKO_USER_CODE,
            "recipient_id": recipient_id,
            "amount": amount,
            "customer_id": customer_id
        }

        return self.make_request("POST", endpoint, data=payload)

    def initiate_transaction(self, customer_id, recipient_id, amount, otp, otp_ref_id, latlong="26.8467,80.9462", recipient_id_type="1", currency="INR", state="1"):
        """Initiate Transaction - POST /v3/customer/payment/dmt-fino"""
        endpoint = f"/v3/customer/payment/dmt-fino"

        from datetime import datetime
        client_ref_id = f"TXN{int(time.time())}"

        payload = {
            "initiator_id": self.initiator_id,
            "user_code": self.EKO_USER_CODE,
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

eko_service = EkoAPIService()