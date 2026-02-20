import requests
import time
import base64
import hmac
import hashlib
import os
import logging

logger = logging.getLogger(__name__)


class EkoCreditService:

    def __init__(self):
        self.base_url = "https://api.eko.in:25002/ekoicici/v2"
        self.developer_key = os.getenv("EKO_DEVELOPER_KEY")
        self.access_key = os.getenv("EKO_SECRET_KEY")
        self.initiator_id = os.getenv("EKO_INITIATOR_ID")
        self.user_code = os.getenv("EKO_USER_CODE")
        self.timeout = 30

    def _generate_timestamp(self):
        return str(int(time.time() * 1000))

    def _generate_secret_key(self, timestamp):
        encoded_key = base64.b64encode(self.access_key.encode()).decode()

        secret_key_hmac = hmac.new(
            encoded_key.encode(),
            timestamp.encode(),
            hashlib.sha256
        ).digest()

        return base64.b64encode(secret_key_hmac).decode()

    def generate_creditlink_url(self, sub_id=None, sub_id2=None):

        timestamp = self._generate_timestamp()
        secret_key = self._generate_secret_key(timestamp)

        headers = {
            "developer_key": self.developer_key,
            "secret-key": secret_key,
            "secret-key-timestamp": timestamp,
            "Content-Type": "application/json",
            "accept": "application/json"
        }

        params = {
            "initiator_id": self.initiator_id,
            "user_code": self.user_code
        }

        if sub_id:
            params["sub_id"] = sub_id
        if sub_id2:
            params["sub_id2"] = sub_id2

        url = f"{self.base_url}/users/payment/redirection/creditlinks-personal-loan"

        try:
            response = requests.get(
                url,
                headers=headers,
                params=params,
                timeout=self.timeout,
                verify=True
            )

            logger.info(f"CreditLink Request URL: {response.url}")
            logger.info(f"CreditLink Response: {response.text}")

            return response.json()

        except requests.exceptions.Timeout:
            return {"status": 1, "message": "Request Timeout"}

        except Exception as e:
            logger.error(str(e))
            return {"status": 1, "message": str(e)}