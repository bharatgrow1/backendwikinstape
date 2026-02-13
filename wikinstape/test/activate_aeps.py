import requests
import json

url = "http://192.168.29.196:8000/apis/merchants/activate/"

token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzcwOTgyNTY0LCJpYXQiOjE3NzA4OTYxNjQsImp0aSI6ImE3ZDZmODViMGZjOTQwZmVhMDBkMjU5M2E3YmYxMDNkIiwidXNlcl9pZCI6IjYifQ.SbJtZrzqv8HEewvKSe3-Nbuss0ucXmnHLrj1mZaEMIs"

headers = {
    "Authorization": f"Bearer {token}"
}

address_as_per_proof = {
    "line": "Shop No 12 Market",
    "city": "Delhi",
    "state": "Delhi",
    "pincode": "110001",
    "state_id": "30"
}

office_address = {
    "line": "Shop No 12 Market",
    "city": "Delhi",
    "state": "Delhi",
    "pincode": "110001",
    "state_id": "30"
}

data = {
    "user_code": "38130001",
    "shop_type": "5411",
    "modelname": "MFS100",
    "devicenumber": "MANTRA12345678",
    "latlong": "28.6167,77.3321",
    "aadhar": "715602244426",
    "account": "9924000100007471",
    "ifsc": "PUNB0992400",
    "address_as_per_proof": json.dumps(address_as_per_proof),
    "office_address": json.dumps(office_address)
}

files = {
    "pan_card": open("pan_card.jpeg", "rb"),
    "aadhar_front": open("aadhar_front.jpeg", "rb"),
    "aadhar_back": open("aadhar_back.jpeg", "rb"),
}

response = requests.post(url, headers=headers, data=data, files=files)

print("Status Code:", response.status_code)
print("Response:", response.text)