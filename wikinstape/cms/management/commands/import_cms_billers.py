import csv
import os
from django.core.management.base import BaseCommand
from django.conf import settings
from cms.models import CMSBiller


class Command(BaseCommand):
    help = "Import CMS billers from CSV"

    def handle(self, *args, **kwargs):

        # ✅ Correct absolute path using BASE_DIR
        csv_path = os.path.join(
            settings.BASE_DIR,
            "Biller-list-CMs.csv"
        )

        if not os.path.exists(csv_path):
            self.stdout.write(
                self.style.ERROR(f"❌ CSV file not found at: {csv_path}")
            )
            return

        with open(csv_path, encoding="utf-8") as f:
            reader = csv.DictReader(f)

            for row in reader:
                operator = row["OPERATOR NAME"].strip()
                biller_id = row["Biller ID"].strip()

                biller_type = "agent" if "AGENT" in operator.upper() else "customer"
                company_name = operator.split("_")[0].strip()

                CMSBiller.objects.update_or_create(
                    biller_id=biller_id,
                    defaults={
                        "operator_name": operator,
                        "company_name": company_name,
                        "biller_type": biller_type,
                        "is_active": True
                    }
                )

        self.stdout.write(
            self.style.SUCCESS("✅ CMS Billers Imported Successfully")
        )
