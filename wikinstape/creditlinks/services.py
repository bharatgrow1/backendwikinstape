import requests
from django.conf import settings
from datetime import datetime


BASE_URL = settings.CREDIT_LINKS_BASE_URL
API_KEY = settings.CREDIT_LINKS_API_KEY


def headers():
    return {
        "apikey": API_KEY,
        "Content-Type": "application/json"
    }


def consent_time():
    return datetime.now().strftime("%Y-%m-%d %H-%M-%S")



def map_employment(status):
    status = str(status).lower()

    if status in ["1", "salaried"]:
        return 1
    elif status in ["2", "self-employed", "self employed"]:
        return 2
    return 1


def get_credit_score_class(score):
    if not score:
        return None

    score = int(score)

    if score >= 730:
        return 1
    elif 680 <= score <= 729:
        return 2
    else:
        return 3


def handle_response(response):
    try:
        data = response.json()
    except Exception:
        data = {"error": "Invalid response from CreditLinks"}

    return {
        "status_code": response.status_code,
        "data": data
    }


def dedupe_api(mobile):
    url = f"{BASE_URL}/api/partner/dedupe"

    payload = {"mobileNumber": mobile}

    response = requests.post(
        url,
        json=payload,
        headers=headers(),
        timeout=30
    )

    return handle_response(response)



def create_personal_loan(data):
    url = f"{BASE_URL}/api/v2/partner/create-lead"

    employment_status = map_employment(data["employment_status"])

    payload = {
        "mobileNumber": data["mobile"],
        "firstName": data["first_name"],
        "lastName": data["last_name"],
        "pan": data["pan_number"],
        "dob": data["dob"],
        "email": data["email"],
        "pincode": data["pincode"],
        "monthlyIncome": data["monthly_income"],
        "creditScoreClass": get_credit_score_class(data.get("credit_score")),
        "consumerConsentDate": consent_time(),
        "consumerConsentIp": "0.0.0.0",
        "employmentStatus": employment_status,
        "waitForAllOffers": 1,
    }

    if employment_status == 1:
        payload.update({
            "employerName": data.get("employer_name"),
            "officePincode": data.get("office_pin_code"),
        })

    if employment_status == 2:
        payload.update({
            "businessRegistrationType": data.get("business_registration_type"),
            "residenceType": data.get("residence_type"),
            "businessCurrentTurnover": data.get("business_current_turnover"),
            "businessYears": data.get("business_years"),
            "businessAccount": data.get("business_account"),
        })

    response = requests.post(
        url,
        json=payload,
        headers=headers(),
        timeout=30
    )

    return handle_response(response)


def update_lead(lead_id, data):
    url = f"{BASE_URL}/api/v2/partner/update-lead/{lead_id}"

    response = requests.post(
        url,
        json=data,
        headers=headers(),
        timeout=30
    )

    return handle_response(response)


def get_offers(lead_id):
    url = f"{BASE_URL}/api/partner/get-offers/{lead_id}"

    response = requests.get(
        url,
        headers=headers(),
        timeout=30
    )

    return handle_response(response)


def get_summary(lead_id):
    url = f"{BASE_URL}/api/partner/get-summary/{lead_id}"

    response = requests.get(
        url,
        headers=headers(),
        timeout=30
    )

    return handle_response(response)



def create_gold_loan(data):
    url = f"{BASE_URL}/api/v2/partner/gold-loans"

    payload = {
        "mobileNumber": data["mobile"],
        "firstName": data["first_name"],
        "lastName": data["last_name"],
        "pan": data.get("pan_number"),
        "email": data["email"],
        "pincode": data["pincode"],
        "loanAmount": data["loan_amount"],
        "consumerConsentDate": consent_time(),
        "consumerConsentIp": "0.0.0.0",
    }

    response = requests.post(
        url,
        json=payload,
        headers=headers(),
        timeout=30
    )

    return handle_response(response)


def gold_status(lead_id):
    url = f"{BASE_URL}/api/v2/partner/gold-loans-status/{lead_id}"

    response = requests.get(
        url,
        headers=headers(),
        timeout=30
    )

    return handle_response(response)


def create_housing_loan(data):
    url = f"{BASE_URL}/api/v2/partner/housing-loan"

    payload = {
        "mobileNumber": data["mobile"],
        "firstName": data["first_name"],
        "lastName": data["last_name"],
        "pan": data["pan_number"],
        "dob": data["dob"],
        "email": data["email"],
        "pincode": data["pincode"],
        "monthlyIncome": data["monthly_income"],
        "housingLoanAmount": data["loan_amount"],
        "propertyType": data["property_type"],
        "consumerConsentDate": consent_time(),
        "consumerConsentIp": "0.0.0.0",
    }

    response = requests.post(
        url,
        json=payload,
        headers=headers(),
        timeout=30
    )

    return handle_response(response)
