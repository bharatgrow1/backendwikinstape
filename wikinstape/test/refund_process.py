import requests
import time
import base64
import hmac
import hashlib
import json

# CONFIG
BASE_URL = "https://api.eko.in:25002/ekoicici"
DEVELOPER_KEY = "753595f07a59eb5a52341538fad5a63d"
ACCESS_KEY = "854313b5-a37a-445a-8bc5-a27f4f0fe56a"
INITIATOR_ID = "9212094999"
USER_CODE = "38130001"

TID = "3512035794" 
OTP = "123456"   


def generate_signature():
    timestamp = str(int(time.time() * 1000))
    encoded_key = base64.b64encode(ACCESS_KEY.encode()).decode()
    hashed = hmac.new(encoded_key.encode(), timestamp.encode(), hashlib.sha256).digest()
    secret_key = base64.b64encode(hashed).decode()
    return secret_key, timestamp


def process_refund(tid, otp):
    secret_key, ts = generate_signature()

    endpoint = f"/v2/transactions/{tid}/refund"
    url = f"{BASE_URL}{endpoint}"

    headers = {
        "accept": "application/json",
        "developer_key": DEVELOPER_KEY,
        "secret-key": secret_key,
        "secret-key-timestamp": ts,
        "Content-Type": "application/x-www-form-urlencoded"
    }

    payload = {
        "initiator_id": INITIATOR_ID,
        "otp": otp,
        "state": 1,
        "user_code": USER_CODE
    }

    print(f"\n🔹 INITIATING REFUND for TID: {tid}")
    print(f"🔸 URL: {url}\n")

    response = requests.post(url, headers=headers, data=payload)
    
    print(f"HTTP {response.status_code}")
    try:
        print(json.dumps(response.json(), indent=4))
    except:
        print(response.text)


if __name__ == "__main__":
    process_refund(TID, OTP)
