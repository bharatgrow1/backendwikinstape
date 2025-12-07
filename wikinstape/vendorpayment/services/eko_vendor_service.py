import requests
import time
import base64
import hmac
import hashlib
import json

class EkoVendorService:
    BASE_URL = "https://api.eko.in:25002/ekoicici"
    DEVELOPER_KEY = "753595f07a59eb5a52341538fad5a63d"
    ACCESS_KEY = "854313b5-a37a-445a-8bc5-a27f4f0fe56a"
    INITIATOR_ID = "9212094999"
    USER_CODE = "38130001"

    def generate_secret(self):
        ts = str(int(time.time() * 1000))
        encoded = base64.b64encode(self.ACCESS_KEY.encode()).decode()
        hashed = hmac.new(encoded.encode(), ts.encode(), hashlib.sha256).digest()
        secret = base64.b64encode(hashed).decode()
        return secret, ts

    def make_request(self, method, endpoint, data=None):
        secret, timestamp = self.generate_secret()

        headers = {
            "developer_key": self.DEVELOPER_KEY,
            "secret-key": secret,
            "secret-key-timestamp": timestamp,
            "accept": "application/json",
            "content-type": "application/x-www-form-urlencoded"
        }

        url = self.BASE_URL + endpoint

        if method == "POST":
            response = requests.post(url, headers=headers, data=data)
        elif method == "GET":
            response = requests.get(url, headers=headers, params=data)
        else:
            raise ValueError("Invalid method")

        return response.json()

    def initiate_payment(self, payload):
        endpoint = f"/v1/agent/user_code:{self.USER_CODE}/settlement"
        return self.make_request("POST", endpoint, payload)