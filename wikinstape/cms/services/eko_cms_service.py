import requests, time, base64, hmac, hashlib, os

class EkoCMSService:

    BASE_URL = "https://api.eko.in:25002/ekoicici/v2/marketuat/airtelPartner"

    def __init__(self):
        self.developer_key = os.getenv("EKO_DEVELOPER_KEY")
        self.secret_key_raw = os.getenv("EKO_SECRET_KEY")
        self.initiator_id = os.getenv("EKO_INITIATOR_ID")


    def _timestamp(self):
        return str(int(time.time() * 1000))

    def _secret_key(self, timestamp):
        encoded = base64.b64encode(self.secret_key_raw.encode())
        digest = hmac.new(encoded, timestamp.encode(), hashlib.sha256).digest()
        return base64.b64encode(digest).decode()

    def _headers(self, timestamp, secret_key):
        return {
            "developer_key": self.developer_key,
            "secret-key-timestamp": timestamp,
            "secret-key": secret_key,
            "Content-Type": "application/json"
        }

    def generate_cms_url(self, payload):
        timestamp = self._timestamp()
        secret_key = self._secret_key(timestamp)

        response = requests.post(
            f"{self.BASE_URL}/generateCmsUrl",
            headers=self._headers(timestamp, secret_key),
            json=payload,
            timeout=30
        )

        return response.json()
