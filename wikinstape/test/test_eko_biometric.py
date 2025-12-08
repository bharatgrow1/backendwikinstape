import time
import base64
import hmac
import hashlib
import requests
from urllib.parse import urlencode

# ----------------------------------------------------
# CONFIGURATION (USE REAL VALUES)
# ----------------------------------------------------

BASE_URL = "https://api.eko.in:25002/ekoicici/v3/customer/account"

developer_key = "753595f07a59eb5a52341538fad5a63d"    # LIVE / TEST DEVELOPER KEY
access_key    = "854313b5-a37a-445a-8bc5-a27f4f0fe56a" # SECRET KEY

customer_id   = "7033596303"   # CUSTOMER MOBILE NUMBER (VERY IMPORTANT)
aadhar        = "405824655319" # ENTER CUSTOMER AADHAR
user_code     = "38130001"     # YOUR EKO USER CODE
initiator_id  = "9212094999"   # YOUR AGENT / SUPER-AGENT ID

# ----------------------------------------------------
# RAW PID DATA (DO NOT FORMAT OR ADD EXTRA SPACES)
# ----------------------------------------------------

piddata = """<?xml version="1.0"?>
<PidData>
  <Resp errCode="0" errInfo="Success." fCount="1" fType="0" nmPoints="39" qScore="70" />
  <DeviceInfo dpId="MANTRA.MSIPL" rdsId="RENESAS.MANTRA.001" rdsVer="1.4.1" mi="MFS110" mc="abcd123">
    <additional_info>
      <Param name="srno" value="10195143" />
      <Param name="sysid" value="6A9FEBF6A28A8B8FBFF0" />
      <Param name="ts" value="2025-12-08T18:32:56+05:30" />
      <Param name="modality_type" value="Finger" />
      <Param name="device_type" value="L1" />
    </additional_info>
  </DeviceInfo>
  <Skey ci="20280813">YOUR-ENCRYPTED-SKEY</Skey>
  <Hmac>YOUR-HMAC</Hmac>
  <Data type="X">YOUR-ENCRYPTED-DATA</Data>
</PidData>
"""

# Remove formatting issues that can break XML
piddata = piddata.strip()

# ----------------------------------------------------
# GENERATE EKO SECRET KEY SIGNATURE
# ----------------------------------------------------

timestamp = str(int(time.time() * 1000))

encoded_key = base64.b64encode(access_key.encode())
hmac_digest = hmac.new(encoded_key, timestamp.encode(), hashlib.sha256).digest()
secret_key = base64.b64encode(hmac_digest).decode()

# ----------------------------------------------------
# REQUEST SETUP
# ----------------------------------------------------

url = f"{BASE_URL}/{customer_id}/dmt-fino/ekyc"

headers = {
    "developer_key": developer_key,
    "secret-key": secret_key,
    "secret-key-timestamp": timestamp,
    "Content-Type": "application/x-www-form-urlencoded"
}

body = {
    "initiator_id": initiator_id,
    "user_code": user_code,
    "aadhar": aadhar,
    "piddata": piddata
}

print("\n=============== REQUEST ===============")
print("URL:", url)
print("Timestamp:", timestamp)
print("Headers:", headers)
print("Body:", "piddata=<XML HIDDEN>")

# ----------------------------------------------------
# SEND REQUEST
# ----------------------------------------------------

response = requests.post(url, headers=headers, data=urlencode(body), verify=False)

print("\n=============== RESPONSE ===============")
print("Status:", response.status_code)
print("Response:", response.text)
