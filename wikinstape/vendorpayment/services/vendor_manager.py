import time
from .eko_vendor_service import EkoVendorService
from vendorpayment.models import VendorPayment


class VendorManager:
    def __init__(self):
        self.eko = EkoVendorService()

    def initiate_payment(self, data):
        client_ref_id = f"VP{int(time.time())}"

        payload = {
            "initiator_id": self.eko.INITIATOR_ID,
            "client_ref_id": client_ref_id,
            "service_code": 45,
            "payment_mode": data['payment_mode'],
            "recipient_name": data['recipient_name'],
            "account": data['account'],
            "ifsc": data['ifsc'],
            "amount": data['amount'],
            "source": "NEWCONNECT",
            "sender_name": "VendorService App",
        }

        api_res = self.eko.initiate_payment(payload)

        VendorPayment.objects.create(
            client_ref_id=client_ref_id,
            recipient_name=data['recipient_name'],
            recipient_account=data['account'],
            recipient_ifsc=data['ifsc'],
            amount=data['amount'],
            eko_tid=api_res.get("data", {}).get("tid"),
            status="processing",
        )

        return api_res


vendor_manager = VendorManager()
