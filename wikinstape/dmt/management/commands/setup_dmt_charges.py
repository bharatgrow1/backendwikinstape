from django.core.management.base import BaseCommand
from dmt.models import DMTServiceCharge

class Command(BaseCommand):
    help = 'Setup default DMT service charges'
    
    def handle(self, *args, **options):
        charges_data = [
            {
                'amount_from': 1,
                'amount_to': 1000,
                'charge_type': 'fixed',
                'charge_value': 5,
                'min_charge': 5,
                'max_charge': 5
            },
            {
                'amount_from': 1001,
                'amount_to': 10000,
                'charge_type': 'percentage',
                'charge_value': 0.5,
                'min_charge': 10,
                'max_charge': 50
            },
            {
                'amount_from': 10001,
                'amount_to': 50000,
                'charge_type': 'percentage',
                'charge_value': 0.25,
                'min_charge': 25,
                'max_charge': 125
            }
        ]
        
        for charge_data in charges_data:
            DMTServiceCharge.objects.update_or_create(
                amount_from=charge_data['amount_from'],
                amount_to=charge_data['amount_to'],
                defaults=charge_data
            )
        
        self.stdout.write(
            self.style.SUCCESS('Successfully setup DMT service charges')
        )