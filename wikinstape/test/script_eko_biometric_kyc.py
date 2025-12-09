import time
import base64
import hmac
import hashlib
import requests
from urllib.parse import urlencode

# ----------------------------------------------------
# CONFIG
# ----------------------------------------------------
DEVELOPER_KEY = "753595f07a59eb5a52341538fad5a63d"
ACCESS_KEY    = "854313b5-a37a-445a-8bc5-a27f4f0fe56a"

customer_id   = "6398523316"
aadhar        = "967829951312"
user_code     = "38130001"
initiator_id  = "9212094999"

# ----------------------------------------------------
# LATEST PID DATA (Exactly as device generated)
# ----------------------------------------------------
piddata = """<?xml version="1.0"?>
<PidData>
  <Resp errCode="0" errInfo="Success." fCount="1" fType="0" nmPoints="58" qScore="83" />
  <DeviceInfo dpId="MANTRA.MSIPL" rdsId="RENESAS.MANTRA.001" rdsVer="1.4.1" mi="MFS110" mc="MIIEADCCAuigAwIBAgIINDY1NUJGNEQwDQYJKoZIhvcNAQELBQAwgfwxKjAoBgNVBAMTIURTIE1hbnRyYSBTb2Z0ZWNoIEluZGlhIFB2dCBMdGQgMjFVMFMGA1UEMxNMQi0yMDMgU2hhcGF0aCBIZXhhIE9wcG9zaXRlIEd1amFyYXQgSGlnaCBDb3VydCBTLkcgSGlnaHdheSBBaG1lZGFiYWQgLTM4MDA2MDESMBAGA1UECRMJQUhNRURBQkFEMRAwDgYDVQQIEwdHVUpBUkFUMR0wGwYDVQQLExRURUNITklDQUwgREVQQVJUTUVOVDElMCMGA1UEChMcTWFudHJhIFNvZnRlY2ggSW5kaWEgUHZ0IEx0ZDELMAkGA1UEBhMCSU4wHhcNMjUxMjA4MTIyNDU5WhcNMjYwMzA4MTIzOTQ2WjCBgjEkMCIGCSqGSIb3DQEJARYVc3VwcG9ydEBtYW50cmF0ZWMuY29tMQswCQYDVQQGEwJJTjELMAkGA1UECBMCR0oxEjAQBgNVBAcTCUFobWVkYWJhZDEOMAwGA1UEChMFTVNJUEwxCzAJBgNVBAsTAklUMQ8wDQYDVQQDEwZNRlMxMTAwggEiMA0GCSqGSIb3DQEBAQUAA4IBDwAwggEKAoIBAQCjetXrsNiuKabcWO1JF1RLO77B949RT8ndsG9JQ6oTYc09/xdKow3a1qt5uocjH7p7RD0JPlNaNVt3QPagxok2Cl2UQOg8iAPTK1DWHoUC3N0GR7jwojOVboa1Na3CW8Q5TM7RjTq0IYD0SfqyVLvnz/G9gqaLwbtnIGcjnOHSawyqhjPVWdIXUCihO4M2ScndekNjjXJW56G2eDb7izt6CYKzzao2vrM2GcIZvBVZlOVgr/reW352ijZMmxj+dpupaRIvJF5+UdjBwQMRpIKtSHYfEUFqI6y35TBTYaK7EnYyc6CeL9it9AbsAXU6QvEN+BiZ28PQqtGm8HknJVOJAgMBAAEwDQYJKoZIhvcNAQELBQADggEBAMei66IQshICmf9xwDrs4fZfiYs9ZxHFOtpnvdY3VhkE+f3KAfi2eCr5sTcyzfQ12JxdXbDjFnhYsnlagNuVj8zRWbmf8EMj3a5Pjzf6wjmeBtywRC8AFdm2v/yNeyzDBxYkkAMmVL9UQzC6bDAH+Ib/yWQt4Ki0dApVpWsY2Hp22i0acDl6xTwoZHem790DHrkaSasf7Uf09qfJ2OEBHos0joJzixOcN0EQSSlELn2D5isusPshdlI7AhMoELzBzxcxzNz8Tm/jFW+7yQBAoeyWqihmE9RmYWR8lTSXH3NP6iVouirA+wYjE8Fn8JZyionuppj30wzTowiwXkL5xsI=" dc="efa43d54-309f-4f15-899a-9ebbf5c9155d">
    <additional_info>
      <Param name="srno" value="10195143" />
      <Param name="sysid" value="6A9FEBF6A28A8B8FBFF0" />
      <Param name="ts" value="2025-12-09T15:38:39+05:30" />
      <Param name="modality_type" value="Finger" />
      <Param name="device_type" value="L1" />
    </additional_info>
  </DeviceInfo>
  <Skey ci="20280813">LwEKpg1FcHiuFacqUTOWKoCWq5uhkrL/q4jX6JEu5PKiY7P+lpA/Bio8nO1N951N2d1GxwxE078bTORji6TGkO4JB4RU/d1Wl+UerU2LsugKj5mVYjP4zjhaOatrfhvHRGfbZB7LKpnTx8k5tWuv/smISbGxv56BcQuy0hRs/ntrvaZJ9TcpOCvH+1Oscl7SyCwtPWUUQBP+F7/3Gj23mGEynYbyjvYLaA2f9McuNiY23gJrc/nVL2dmQHOW5IvsxuuxDAXeAvaKCCzGuLX3zd6Hdgvl4DXwUNDIX6VbjaxwXRpQQw00fdrV9FIQiYG1BoX12f3dABMQD9+Gk8KMWg==</Skey>
  <Hmac>HJn+S/KqRwaEA8A38DSfQtAZhw+WC940GIfzyGP43Gx/BqeljVysnJ2NVLvoC0nc</Hmac>
  <Data type="X">MjAyNS0xMi0wOVQxNTozODozMDBi5dI+yu7fUNDQT4HEus3c5AkXevZngUdVQyWqvynjQ9hWEG84uD13Hh98cDJQ5MA359geMS28x65q0rAtQrHpMWWb5d7ARjbBrCLJwMPn290J8JJJby8Vv8WThTPUfnXSLCK8SOApA4ejgVMjAnkv747nCckfNR5x6UidKWLD3GUn5F+pMU6qb0QVALCGxI20UIX2EBqNy58XhTna... (VERY LONG DATA)
</Data>
</PidData>
"""

# ----------------------------------------------------
# SECRET KEY FUNCTION
# ----------------------------------------------------
def generate_secret_key(access_key):
    ts = str(int(time.time() * 1000))
    key = base64.b64encode(access_key.encode())
    digest = hmac.new(key, ts.encode(), hashlib.sha256).digest()
    return ts, base64.b64encode(digest).decode()

# ----------------------------------------------------
# SEND EKYC OTP
# ----------------------------------------------------
def send_ekyc_otp():
    ts, sk = generate_secret_key(ACCESS_KEY)

    url = f"https://api.eko.in:25002/ekoicici/v3/customer/account/{customer_id}/dmt-fino/ekyc"

    headers = {
        "developer_key": DEVELOPER_KEY,
        "secret-key": sk,
        "secret-key-timestamp": ts,
        "Content-Type": "application/x-www-form-urlencoded"
    }

    body = {
        "initiator_id": initiator_id,
        "user_code": user_code,
        "customer_id": customer_id,
        "aadhar": aadhar,
        "piddata": piddata
    }

    res = requests.post(url, headers=headers, data=urlencode(body), verify=False)
    print("\n=== EKYC OTP RESPONSE ===")
    print(res.text)
    return res.text

# ----------------------------------------------------
# MAIN
# ----------------------------------------------------
if __name__ == "__main__":
    send_ekyc_otp()
