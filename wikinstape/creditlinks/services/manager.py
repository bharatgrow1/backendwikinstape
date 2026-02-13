from .eko_credit_service import EkoCreditService


class CreditLinkManager:

    def __init__(self):
        self.service = EkoCreditService()

    def generate_link(self, user):

        response = self.service.generate_creditlink_url(
            sub_id=user.id,
            sub_id2=user.mobile if hasattr(user, "mobile") else None
        )

        if response.get("status") == 0:
            return {
                "success": True,
                "redirect_url": response.get("data", {}).get("redirect_url"),
                "response_status_id": response.get("response_status_id"),
                "response_type_id": response.get("response_type_id"),
                "message": response.get("message"),
                "raw": response
            }

        return {
            "success": False,
            "message": response.get("message"),
            "raw": response
        }


credit_manager = CreditLinkManager()
