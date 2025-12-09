import time
import base64
import hmac
import hashlib
import requests
from urllib.parse import urlencode

BASE_URL = "https://api.eko.in:25002/ekoicici/v3/customer/account"

developer_key = "753595f07a59eb5a52341538fad5a63d"
access_key    = "854313b5-a37a-445a-8bc5-a27f4f0fe56a"

customer_id   = "6398523316"
aadhar        = "967829951312"
user_code     = "38130001"
initiator_id  = "9212094999"

# ------------------------------
# UPDATED REAL PID DATA
# ------------------------------

piddata = """<?xml version="1.0"?>
<PidData>
  <Resp errCode="0" errInfo="Success." fCount="1" fType="0" nmPoints="44" qScore="94" />
  <DeviceInfo dpId="MANTRA.MSIPL" rdsId="RENESAS.MANTRA.001" rdsVer="1.4.1" mi="MFS110" mc="MIIEADCCAuigAwIBAgIINDY1NUJGNEQwDQYJKoZIhvcNAQELBQAwgfwxKjAoBgNVBAMTIURTIE1hbnRyYSBTb2Z0ZWNoIEluZGlhIFB2dCBMdGQgMjFVMFMGA1UEMxNMQi0yMDMgU2hhcGF0aCBIZXhhIE9wcG9zaXRlIEd1amFyYXQgSGlnaCBDb3VydCBTLkcgSGlnaHdheSBBaG1lZGFiYWQgLTM4MDA2MDESMBAGA1UECRMJQUhNRURBQkFEMRAwDgYDVQQIEwdHVUpBUkFUMR0wGwYDVQQLExRURUNITklDQUwgREVQQVJUTUVOVDElMCMGA1UEChMcTWFudHJhIFNvZnRlY2ggSW5kaWEgUHZ0IEx0ZDELMAkGA1UEBhMCSU4wHhcNMjUxMjA4MTIyNDU5WhcNMjYwMzA4MTIzOTQ2WjCBgjEkMCIGCSqGSIb3DQEJARYVc3VwcG9ydEBtYW50cmF0ZWMuY29tMQswCQYDVQQGEwJJTjELMAkGA1UECBMCR0oxEjAQBgNVBAcTCUFobWVkYWJhZDEOMAwGA1UEChMFTVNJUEwxCzAJBgNVBAsTAklUMQ8wDQYDVQQDEwZNRlMxMTAwggEiMA0GCSqGSIb3DQEBAQUAA4IBDwAwggEKAoIBAQCjetXrsNiuKabcWO1JF1RLO77B949RT8ndsG9JQ6oTYc09/xdKow3a1qt5uocjH7p7RD0JPlNaNVt3QPagxok2Cl2UQOg8iAPTK1DWHoUC3N0GR7jwojOVboa1Na3CW8Q5TM7RjTq0IYD0SfqyVLvnz/G9gqaLwbtnIGcjnOHSawyqhjPVWdIXUCihO4M2ScndekNjjXJW56G2eDb7izt6CYKzzao2vrM2GcIZvBVZlOVgr/reW352ijZMmxj+dpupaRIvJF5+UdjBwQMRpIKtSHYfEUFqI6y35TBTYaK7EnYyc6CeL9it9AbsAXU6QvEN+BiZ28PQqtGm8HknJVOJAgMBAAEwDQYJKoZIhvcNAQELBQADggEBAMei66IQshICmf9xwDrs4fZfiYs9ZxHFOtpnvdY3VhkE+f3KAfi2eCr5sTcyzfQ12JxdXbDjFnhYsnlagNuVj8zRWbmf8EMj3a5Pjzf6wjmeBtywRC8AFdm2v/yNeyzDBxYkkAMmVL9UQzC6bDAH+Ib/yWQt4Ki0dApVpWsY2Hp22i0acDl6xTwoZHem790DHrkaSasf7Uf09qfJ2OEBHos0joJzixOcN0EQSSlELn2D5isusPshdlI7AhMoELzBzxcxzNz8Tm/jFW+7yQBAoeyWqihmE9RmYWR8lTSXH3NP6iVouirA+wYjE8Fn8JZyionuppj30wzTowiwXkL5xsI=" dc="efa43d54-309f-4f15-899a-9ebbf5c9155d">
    <additional_info>
      <Param name="srno" value="10195143"/>
      <Param name="sysid" value="6A9FEBF6A28A8B8FBFF0"/>
      <Param name="ts" value="2025-12-09T14:21:47+05:30"/>
      <Param name="modality_type" value="Finger"/>
      <Param name="device_type" value="L1"/>
    </additional_info>
  </DeviceInfo>
  <Skey ci="20280813">ld4YrhGpJMrGJBPLfs9axkcC2aOQz3g7wpjNh/A5zBdRJOuN2pSOz2sRhmpgueKhpmN+/qWx34Ek5ZKHKN76X5pbXxDKbMlTvsoJx8EdsI3cmtJFa9V6mz3arLhZ2eO4W/y/omT8zU5KozYE4o3vFeSsKaNR1UaIRjTyY4ST4rx4XPTiS2vTt1EH8qdI1sXhjQvs8fgdXrL7UcO4VDvNhbj4S160/oEesSPlc/WNA++nuisG8IbV6Q558ryRuQ2dlWQ2/DMv6WnheWXwgESRziddGu17FrpDEvdiNhT8NBpYqB0DJeal4O+rGivTrchB8ViLq8YbRRGYI9dnjv8ITw==</Skey>
  <Hmac>eIyiIpmkB4FzHHpFZCvuuZ2kV5vEfLLhuRktW6BxxJK3iRJKjz2osyRl3mn3BWjP</Hmac>
  <Data type="X">MjAyNS0xMi0wOVQxNDoyMTo0MF+Qu8553WEzmUN8K3BvfzQ7ep9W+6Tv0bzjq9zrOr5N/oqwrtgz72+b0AkBrcq8DbPRaUk...</Data>
</PidData>
"""

piddata = piddata.strip()

# ------------------------------
# GENERATE SECRET KEY
# ------------------------------

timestamp = str(int(time.time() * 1000))
encoded_key = base64.b64encode(access_key.encode())
hmac_digest = hmac.new(encoded_key, timestamp.encode(), hashlib.sha256).digest()
secret_key = base64.b64encode(hmac_digest).decode()

# ------------------------------
# CORRECT EKO REQUEST (IMPORTANT)
# ------------------------------

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
    "customer_id": customer_id,     # REQUIRED FIELD ADDED
    "piddata": piddata
}

print("\n=============== REQUEST ===============")
print("URL:", url)
print("Timestamp:", timestamp)
print("Headers:", headers)
print("Body:", "piddata=<XML HIDDEN>")

response = requests.post(url, headers=headers, data=urlencode(body), verify=False)

print("\n=============== RESPONSE ===============")
print("Status:", response.status_code)
print("Response:", response.text)
