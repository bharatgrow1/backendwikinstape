import requests
import time
import base64
import hmac
import hashlib
import json

# -----------------------------------
# CONFIGURATION
# -----------------------------------
BASE_URL = "https://api.eko.in:25002/ekoicici" 
DEVELOPER_KEY = "753595f07a59eb5a52341538fad5a63d"
ACCESS_KEY = "854313b5-a37a-445a-8bc5-a27f4f0fe56a"
INITIATOR_ID = "9212094999"
USER_CODE = "38130001"

# Transaction Details
CLIENT_REF_ID = f"VP{int(time.time())}"
BENEFICIARY_NAME = "Pritesh Prasad"
BENEFICIARY_ACCOUNT = "9924000100007471"
BENEFICIARY_IFSC = "PUNB0992400"
AMOUNT = 10
PAYMENT_MODE = 5   # 5=IMPS, 4=NEFT, 13=RTGS

# -----------------------------------
def generate_signature():
    timestamp = str(int(time.time() * 1000))
    encoded_key = base64.b64encode(ACCESS_KEY.encode()).decode()
    hashed = hmac.new(encoded_key.encode(), timestamp.encode(), hashlib.sha256).digest()
    secret_key = base64.b64encode(hashed).decode()
    return secret_key, timestamp


def vendor_payment():
    secret_key, ts = generate_signature()

    endpoint = f"/v1/agent/user_code:{USER_CODE}/settlement"
    url = f"{BASE_URL}{endpoint}"

    headers = {
        "accept": "application/json",
        "developer_key": DEVELOPER_KEY,
        "secret-key": secret_key,
        "secret-key-timestamp": ts,
        "content-type": "application/x-www-form-urlencoded"
    }

    payload = {
        "initiator_id": INITIATOR_ID,
        "client_ref_id": CLIENT_REF_ID,
        "service_code": 45,
        "payment_mode": PAYMENT_MODE,
        "recipient_name": BENEFICIARY_NAME,
        "account": BENEFICIARY_ACCOUNT,
        "ifsc": BENEFICIARY_IFSC,
        "amount": AMOUNT,
        "source": "NEWCONNECT",
        "sender_name": "Pritesh Enterprises",
        "tag": "Vendor Payment"
    }

    print("\n🔹 Initiating Vendor Payment")
    print(f"🔸 URL: {url}")
    print(f"🔸 Payload: {payload}\n")

    response = requests.post(url, headers=headers, data=payload)
    print(f"HTTP {response.status_code}\n")

    try:
        data = response.json()
        print(json.dumps(data, indent=4))
        return data
    except:
        print(response.text)
        return None


if __name__ == "__main__":
    vendor_payment()
