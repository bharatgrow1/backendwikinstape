import requests

pid_options = """<?xml version="1.0"?>
<PidOptions ver="1.0">
    <Opts fCount="1" fType="0" format="0" pidVer="2.0" timeout="20000" env="P"/>
</PidOptions>
"""

url = "http://127.0.0.1:11100/rd/capture?ts="   # VERY IMPORTANT

headers = {
    "Content-Type": "application/xml",
    "Accept": "application/xml"
}

print("Sending request to Mantra RD Service...")

response = requests.post(url, data=pid_options, headers=headers)

print("\n===== RESPONSE =====")
print("STATUS:", response.status_code)
print("BODY:\n", response.text)
