# recharge/management/commands/setup_recharge_service.py
from django.core.management.base import BaseCommand
from services.models import ServiceCategory, ServiceSubCategory
from commission.models import ServiceCommission, CommissionPlan
from django.contrib.auth import get_user_model

User = get_user_model()

class Command(BaseCommand):
    help = 'Setup recharge service category and commission configuration'
    
    def handle(self, *args, **options):
        # Get or create superadmin
        superadmin = User.objects.filter(role='superadmin').first()
        if not superadmin:
            self.stdout.write(self.style.ERROR('Superadmin user not found'))
            return
        
        # Create recharge category
        recharge_category, created = ServiceCategory.objects.update_or_create(
            name='Mobile Recharge',
            defaults={
                'description': 'Mobile recharge and bill payments',
                'is_active': True,
                'created_by': superadmin,
                'allow_direct_service': False,
                'require_mobile_number': True,
                'require_amount': True,
                'require_operator': True,
            }
        )
        
        # Create recharge subcategory
        recharge_subcategory, created = ServiceSubCategory.objects.update_or_create(
            category=recharge_category,
            name='Mobile Prepaid/Postpaid Recharge',
            defaults={
                'description': 'Mobile prepaid and postpaid recharge services',
                'is_active': True,
                'created_by': superadmin,
                'require_mobile_number': True,
                'require_amount': True,
                'require_operator': True,
                'require_customer_name': True,
            }
        )
        
        recharge_types = [
            ('DTH Recharge', 'DTH and cable TV recharge'),
            ('Electricity Bill', 'Electricity bill payment'),
            ('Water Bill', 'Water bill payment'),
            ('Gas Bill', 'Gas bill payment'),
            ('Broadband Bill', 'Broadband bill payment'),
            ('Landline Bill', 'Landline bill payment'),
            ('Loan EMI Payment', 'Loan EMI bill payment'),
            ('Fastag Recharge', 'FASTag recharging service'),
            ('Credit Card Bill Payment', 'Credit card bill payment'),
            ('Municipal Tax Payment', 'Municipal corporation tax payment'),
            ('Housing Society Maintenance', 'Housing society maintenance charges'),
            ('OTT Subscription Payment', 'OTT subscription renewal'),
            ('Education Fee Payment', 'School or college fee payment'),
            ('Clubs and Associations Payment', 'Club membership fees'),
            ('Cable TV Payment', 'Cable TV service payment'),
            ('LPG Cylinder Payment', 'LPG gas cylinder booking payment'),
            ('Hospital Bill Payment', 'Hospital bill payment'),
            ('Insurance Premium Payment', 'Insurance premium bill'),
            ('Municipal Service Payment', 'Municipal service payment'),
            ('Subscription2 Payment', 'Subscription type 2'),
        ]

        
        for name, description in recharge_types:
            ServiceSubCategory.objects.update_or_create(
                category=recharge_category,
                name=name,
                defaults={
                    'description': description,
                    'is_active': True,
                    'created_by': superadmin,
                }
            )
        
        # Get or create commission plans
        plans = [
            ('platinum', 'Platinum Plan'),
            ('gold', 'Gold Plan'),
            ('silver', 'Silver Plan'),
        ]
        
        for plan_type, plan_name in plans:
            commission_plan, _ = CommissionPlan.objects.update_or_create(
                plan_type=plan_type,
                defaults={
                    'name': plan_name,
                    'is_active': True,
                    'created_by': superadmin
                }
            )
            
            # Create commission configurations for each plan
            commission_data = {
                'platinum': {
                    'commission_type': 'percentage',
                    'commission_value': 2.0,  # 2% commission
                    'admin_commission': 10,
                    'master_commission': 15,
                    'dealer_commission': 20,
                    'retailer_commission': 25,
                },
                'gold': {
                    'commission_type': 'percentage',
                    'commission_value': 1.5,  # 1.5% commission
                    'admin_commission': 10,
                    'master_commission': 15,
                    'dealer_commission': 20,
                    'retailer_commission': 25,
                },
                'silver': {
                    'commission_type': 'percentage',
                    'commission_value': 1.0,  # 1% commission
                    'admin_commission': 10,
                    'master_commission': 15,
                    'dealer_commission': 20,
                    'retailer_commission': 25,
                }
            }
            
            config_data = commission_data.get(plan_type)
            if config_data:
                ServiceCommission.objects.update_or_create(
                    service_subcategory=recharge_subcategory,
                    commission_plan=commission_plan,
                    defaults={
                        **config_data,
                        'is_active': True,
                        'created_by': superadmin
                    }
                )
        
        self.stdout.write(self.style.SUCCESS(
            f'✅ Created recharge service category: {recharge_category.name}'
        ))
        self.stdout.write(self.style.SUCCESS(
            f'✅ Created recharge service subcategory: {recharge_subcategory.name}'
        ))
        self.stdout.write(self.style.SUCCESS(
            f'✅ Created commission configurations for recharge service'
        ))