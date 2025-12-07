import requests
import time
import base64
import hmac
import hashlib
import json

# -----------------------------------
# 🔧 CONFIGURATION
# -----------------------------------
BASE_URL = "https://api.eko.in:25002/ekoicici"  # ✅ Correct base URL for transaction inquiry
DEVELOPER_KEY = "753595f07a59eb5a52341538fad5a63d"
ACCESS_KEY = "854313b5-a37a-445a-8bc5-a27f4f0fe56a"
INITIATOR_ID = "9212094999"
USER_CODE = "38130001"

# 🔹 ID to test
INQUIRY_ID = "3513729402"
IS_CLIENT_REF_ID = False  # True → client_ref_id:xxxx

# -----------------------------------
def generate_signature():
    timestamp = str(int(time.time() * 1000))
    encoded_key = base64.b64encode(ACCESS_KEY.encode()).decode()
    hashed = hmac.new(encoded_key.encode(), timestamp.encode(), hashlib.sha256).digest()
    secret_key = base64.b64encode(hashed).decode()
    return secret_key, timestamp


def transaction_inquiry(inquiry_id, is_client_ref_id=False):
    secret_key, ts = generate_signature()

    if is_client_ref_id:
        endpoint = f"/v1/transactions/client_ref_id:{inquiry_id}"
    else:
        endpoint = f"/v1/transactions/{inquiry_id}"

    url = f"{BASE_URL}{endpoint}"

    headers = {
        "accept": "application/json",
        "developer_key": DEVELOPER_KEY,
        "secret-key": secret_key,
        "secret-key-timestamp": ts
    }

    params = {
        "initiator_id": INITIATOR_ID,
        "user_code": USER_CODE
    }

    print(f"\n🔹 Checking transaction status for: {inquiry_id}")
    print(f"🔸 URL: {url}")
    print(f"🔸 Headers: {headers}")
    print(f"🔸 Params: {params}\n")

    response = requests.get(url, headers=headers, params=params)
    print(f"HTTP {response.status_code}")

    try:
        data = response.json()
        print(json.dumps(data, indent=4))
        return data
    except:
        print(response.text)
        return None


if __name__ == "__main__":
    transaction_inquiry(INQUIRY_ID, IS_CLIENT_REF_ID)
