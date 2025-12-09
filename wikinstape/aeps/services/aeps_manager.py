from .aeps_service import EkoAEPSService
from aeps.models import AEPSMerchant

class AEPSManager:
    def onboard_merchant(self, data):
        eko = EkoAEPSService()
        api = eko.onboard_merchant(data)

        if api.get("response_type_id") == 1290:
            user_code = api["data"]["user_code"]

            AEPSMerchant.objects.create(
                user_code=user_code,
                merchant_name=f"{data['first_name']} {data.get('last_name', '')}".strip(),
                shop_name=data["shop_name"],
                mobile=data["mobile"],
                email=data["email"],
                pan_number=data["pan_number"],
                address_line=data["address_line"],
                city=data["city"],
                state=data["state"],
                pincode=data["pincode"],
                district=data.get("district", ""),
                area=data.get("area", "")
            )

            return {
                "success": True,
                "message": "Merchant onboarded successfully",
                "user_code": user_code
            }

        return {
            "success": False,
            "message": api.get("message", "Onboarding failed"),
            "error": api
        }
