from django.core.management.base import BaseCommand
from services.models import ServiceSubCategory
from eko_integration.models import EkoService

class Command(BaseCommand):
    help = 'Setup Eko services mapping'
    
    def handle(self, *args, **options):
        eko_services_mapping = {
            # BBPS Services
            'Electricity Bill Payment': {'code': 'BBPS_ELECTRICITY', 'name': 'Electricity Bill'},
            'Water Bill Payment': {'code': 'BBPS_WATER', 'name': 'Water Bill'},
            'Gas Bill Payment': {'code': 'BBPS_GAS', 'name': 'Gas Bill'},
            'Broadband Bill': {'code': 'BBPS_BROADBAND', 'name': 'Broadband Bill'},
            
            # Recharge Services
            'Mobile Recharge': {'code': 'RECHARGE', 'name': 'Mobile Recharge'},
            'DTH Recharge': {'code': 'DTH_RECHARGE', 'name': 'DTH Recharge'},
            
            # Money Transfer
            'Money Transfer': {'code': 'MONEY_TRANSFER', 'name': 'Money Transfer'},
        }
        
        for service_name, eko_config in eko_services_mapping.items():
            try:
                subcategory = ServiceSubCategory.objects.get(name=service_name)
                eko_service, created = EkoService.objects.get_or_create(
                    service_subcategory=subcategory,
                    defaults={
                        'eko_service_code': eko_config['code'],
                        'eko_service_name': eko_config['name']
                    }
                )
                
                if created:
                    self.stdout.write(
                        self.style.SUCCESS(f'Created Eko service: {service_name}')
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING(f'Eko service already exists: {service_name}')
                    )
                    
            except ServiceSubCategory.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'Service not found: {service_name}')
                )