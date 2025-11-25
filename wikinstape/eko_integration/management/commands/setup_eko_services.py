from django.core.management.base import BaseCommand
from services.models import ServiceCategory, ServiceSubCategory
from eko_integration.models import EkoService
from django.contrib.auth import get_user_model

User = get_user_model()

class Command(BaseCommand):
    help = "Auto setup/update ALL Services, SubServices & Eko Mappings"

    def handle(self, *args, **options):

        self.stdout.write(self.style.SUCCESS("🔧 Updating all services & Eko mappings..."))

        superadmin = User.objects.filter(role="superadmin").first()
        if not superadmin:
            self.stdout.write(self.style.ERROR("❌ No superadmin found. Create one first."))
            return

        SERVICE_CONFIG = {
            "Bill Payments": {
                "Electricity Bill Payment": {"code": "BBPS_ELECTRICITY", "name": "Electricity Bill"},
                "Water Bill Payment": {"code": "BBPS_WATER", "name": "Water Bill"},
                "Gas Bill Payment": {"code": "BBPS_GAS", "name": "Gas Bill"},
                "Broadband Bill": {"code": "BBPS_BROADBAND", "name": "Broadband Bill"},
                "Loan EMI Payment": {"code": "LOAN_EMI", "name": "Loan EMI Payment"},
                "Fastag Recharge": {"code": "FASTAG", "name": "Fastag Recharge"},
                "Credit Bill Payment": {"code": "CREDIT_CARD", "name": "Credit Card Bill Payment"},
                "Municipal Tax Payment": {"code": "MUNICIPAL_TAX", "name": "Municipal Tax Payment"},
                "Society Maintenance Payment": {"code": "SOCIETY_MAINTENANCE", "name": "Society Maintenance Payment"},
                "Traffic Challan Payment": {"code": "TRAFFIC_CHALLAN", "name": "Traffic Challan Payment"},
                "OTT Subscription Payment": {"code": "OTT", "name": "OTT Subscription Payment"},
                "Education Fee Payment": {"code": "EDUCATION_FEE", "name": "Education Fee Payment"},
                "Rent Payment": {"code": "RENT_PAYMENT", "name": "Rent Payment"},
            },

            "Recharge": {
                "Mobile Recharge": {"code": "RECHARGE", "name": "Mobile Recharge"},
                "DTH Recharge": {"code": "DTH_RECHARGE", "name": "DTH Recharge"},
                "OTT Recharge": {"code": "OTT_RECHARGE", "name": "OTT Recharge"},
            },

            "Money Transfer": {
                "Money Transfer": {"code": "MONEY_TRANSFER", "name": "Money Transfer"},
                "DMT Service": {"code": "DMT", "name": "Domestic Money Transfer"},
            }
        }

        cat_created = sub_created = eko_created = updated = 0

        for category_name, subservices in SERVICE_CONFIG.items():

            category, created = ServiceCategory.objects.get_or_create(
                name=category_name,
                defaults={
                    "description": f"{category_name} Services",
                    "is_active": True,
                    "created_by": superadmin
                }
            )
            if created:
                cat_created += 1
                self.stdout.write(self.style.SUCCESS(f"🟩 Created Category: {category_name}"))

            for sub_name, eko in subservices.items():

                subcategory, created_sub = ServiceSubCategory.objects.get_or_create(
                    category=category,
                    name=sub_name,
                    defaults={
                        "description": f"{sub_name} Service",
                        "is_active": True,
                        "created_by": superadmin
                    }
                )
                if created_sub:
                    sub_created += 1
                    self.stdout.write(self.style.SUCCESS(f"🟧 Created SubCategory: {sub_name}"))

                eko_service, created_eko = EkoService.objects.get_or_create(
                    service_subcategory=subcategory,
                    defaults={
                        "eko_service_code": eko["code"],
                        "eko_service_name": eko["name"],
                        "is_active": True
                    }
                )

                if created_eko:
                    eko_created += 1
                    self.stdout.write(self.style.SUCCESS(f"🟦 Created EkoService: {sub_name}"))
                else:
                    changed = False

                    if eko_service.eko_service_code != eko["code"]:
                        eko_service.eko_service_code = eko["code"]
                        changed = True

                    if eko_service.eko_service_name != eko["name"]:
                        eko_service.eko_service_name = eko["name"]
                        changed = True

                    if not eko_service.is_active:
                        eko_service.is_active = True
                        changed = True

                    if changed:
                        eko_service.save()
                        updated += 1
                        self.stdout.write(self.style.WARNING(f"🔄 Updated EkoService: {sub_name}"))
                    else:
                        self.stdout.write(self.style.SUCCESS(f"✅ Already up-to-date: {sub_name}"))

        # ===================== SUMMARY =======================
        self.stdout.write("\n")
        self.stdout.write(self.style.SUCCESS("========== SUMMARY =========="))
        self.stdout.write(self.style.SUCCESS(f"🟩 Categories Created: {cat_created}"))
        self.stdout.write(self.style.SUCCESS(f"🟧 SubCategories Created: {sub_created}"))
        self.stdout.write(self.style.SUCCESS(f"🟦 EkoServices Created: {eko_created}"))
        self.stdout.write(self.style.WARNING(f"🔄 EkoServices Updated: {updated}"))
        self.stdout.write(self.style.SUCCESS("================================="))
        self.stdout.write(self.style.SUCCESS("🎉 ALL SERVICES SUCCESSFULLY UPDATED!"))
