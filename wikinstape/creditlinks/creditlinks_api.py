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
    if not status:
        return None

    status = str(status).lower()

    if status in ["1", "salaried"]:
        return 1
    elif status in ["2", "self-employed", "self employed"]:
        return 2

    return None


def get_credit_score_class(score):
    if not score:
        return None

    try:
        score = int(score)
    except Exception:
        return None

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
        data = {"success": False, "message": "Invalid response from CreditLinks"}

    return {
        "status_code": response.status_code,
        "data": data
    }


def dedupe_api(mobile):

    if not mobile:
        return {
            "status_code": 400,
            "data": {"success": False, "message": "Mobile is required"}
        }

    url = f"{BASE_URL}/api/partner/dedupe"

    response = requests.post(
        url,
        json={"mobileNumber": mobile},
        headers=headers(),
        timeout=30
    )

    return handle_response(response)


def create_personal_loan(data):

    required_fields = [
        "mobile",
        "first_name",
        "last_name",
        "pan_number",
        "dob",
        "email",
        "pincode",
        "monthly_income",
        "employment_status"
    ]

    missing = [field for field in required_fields if not data.get(field)]

    if missing:
        return {
            "status_code": 400,
            "data": {
                "success": False,
                "message": f"Missing fields: {', '.join(missing)}"
            }
        }

    employment_status = map_employment(data.get("employment_status"))

    if not employment_status:
        return {
            "status_code": 400,
            "data": {
                "success": False,
                "message": "Invalid employment_status"
            }
        }

    payload = {
        "mobileNumber": data.get("mobile"),
        "firstName": data.get("first_name"),
        "lastName": data.get("last_name"),
        "pan": data.get("pan_number"),
        "dob": data.get("dob"),
        "email": data.get("email"),
        "pincode": data.get("pincode"),
        "monthlyIncome": data.get("monthly_income"),
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

    url = f"{BASE_URL}/api/v2/partner/create-lead"

    response = requests.post(
        url,
        json=payload,
        headers=headers(),
        timeout=30
    )

    return handle_response(response)


def update_lead(lead_id, data):

    if not lead_id:
        return {
            "status_code": 400,
            "data": {"success": False, "message": "lead_id is required"}
        }

    url = f"{BASE_URL}/api/v2/partner/update-lead/{lead_id}"

    response = requests.post(
        url,
        json=data,
        headers=headers(),
        timeout=30
    )

    return handle_response(response)



def get_offers(lead_id):

    if not lead_id:
        return {
            "status_code": 400,
            "data": {"success": False, "message": "lead_id is required"}
        }

    url = f"{BASE_URL}/api/partner/get-offers/{lead_id}"

    response = requests.get(
        url,
        headers=headers(),
        timeout=30
    )

    return handle_response(response)



def get_summary(lead_id):

    if not lead_id:
        return {
            "status_code": 400,
            "data": {"success": False, "message": "lead_id is required"}
        }

    url = f"{BASE_URL}/api/partner/get-summary/{lead_id}"

    response = requests.get(
        url,
        headers=headers(),
        timeout=30
    )

    return handle_response(response)


def create_gold_loan(data):

    required_fields = ["mobile", "first_name", "last_name", "email", "pincode", "loan_amount"]

    missing = [field for field in required_fields if not data.get(field)]

    if missing:
        return {
            "status_code": 400,
            "data": {"success": False, "message": f"Missing fields: {', '.join(missing)}"}
        }

    payload = {
        "mobileNumber": data.get("mobile"),
        "firstName": data.get("first_name"),
        "lastName": data.get("last_name"),
        "pan": data.get("pan_number"),
        "email": data.get("email"),
        "pincode": data.get("pincode"),
        "loanAmount": data.get("loan_amount"),
        "consumerConsentDate": consent_time(),
        "consumerConsentIp": "0.0.0.0",
    }

    url = f"{BASE_URL}/api/v2/partner/gold-loans"

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

    required_fields = [
        "mobile",
        "first_name",
        "last_name",
        "pan_number",
        "dob",
        "email",
        "pincode",
        "monthly_income",
        "loan_amount",
        "property_type"
    ]

    missing = [field for field in required_fields if not data.get(field)]

    if missing:
        return {
            "status_code": 400,
            "data": {"success": False, "message": f"Missing fields: {', '.join(missing)}"}
        }

    payload = {
        "mobileNumber": data.get("mobile"),
        "firstName": data.get("first_name"),
        "lastName": data.get("last_name"),
        "pan": data.get("pan_number"),
        "dob": data.get("dob"),
        "email": data.get("email"),
        "pincode": data.get("pincode"),
        "monthlyIncome": data.get("monthly_income"),
        "housingLoanAmount": data.get("loan_amount"),
        "propertyType": data.get("property_type"),
        "consumerConsentDate": consent_time(),
        "consumerConsentIp": "0.0.0.0",
    }

    url = f"{BASE_URL}/api/v2/partner/housing-loan"

    response = requests.post(
        url,
        json=payload,
        headers=headers(),
        timeout=30
    )

    return handle_response(response)