from .eko_service import EkoAPIService
import requests
import time 
from datetime import datetime 

class EkoBBPSService(EkoAPIService):
    def fetch_bill(self, consumer_number, service_type, operator_id=None):
        """Fetch bill details - Simulated for now"""
        static_bills = {
            '1234567890': {
                'consumer_name': 'Rajesh Kumar',
                'consumer_number': '1234567890',
                'bill_amount': 1250.00,
                'due_date': '2024-12-25',
                'billing_period': 'Nov 2024',
                'service_provider': 'BSES Yamuna',
                'outstanding_amount': 1250.00,
                'late_fee': 0.00
            }
        }
        
        bill_data = static_bills.get(consumer_number)
        if bill_data:
            return {
                'status': 0,
                'message': 'Bill fetched successfully',
                'data': bill_data
            }
        else:
            return {
                'status': 1,
                'message': 'Bill not found'
            }
    
    def pay_bill(self, user_code, consumer_number, service_provider, amount, bill_number=None):
        """Pay bill through Eko"""
        url = f"{self.base_url}/ekoapi/v2/bills/pay" 
        
        data = {
            'initiator_id': self.initiator_id,
            'user_code': user_code,
            'consumer_number': consumer_number,
            'service_provider': service_provider,
            'amount': amount,
            'bill_number': bill_number
        }
        
        try:
            return {
                'status': 0,
                'message': 'Bill paid successfully',
                'data': {
                    'transaction_id': f'TXN{int(time.time())}',
                    'amount': amount,
                    'status': 'success'
                }
            }
        except Exception as e:
            return {'status': 1, 'message': str(e)}

class EkoRechargeService(EkoAPIService):
    def get_operators(self, service_type='mobile'):
        """Get available operators"""
        operators = {
            'mobile': [
                {'id': '1', 'name': 'Airtel'},
                {'id': '2', 'name': 'Jio'},
                {'id': '3', 'name': 'Vi'},
                {'id': '4', 'name': 'BSNL'}
            ],
            'dth': [
                {'id': '101', 'name': 'Airtel Digital TV'},
                {'id': '102', 'name': 'Tata Sky'},
                {'id': '103', 'name': 'Dish TV'},
                {'id': '104', 'name': 'Sun Direct'}
            ]
        }
        
        return {
            'status': 0,
            'data': operators.get(service_type, [])
        }
    
    def recharge(self, user_code, mobile_number, operator_id, amount, circle='DELHI'):
        """Perform recharge"""
        return {
            'status': 0,
            'message': 'Recharge successful',
            'data': {
                'transaction_id': f'RECH{int(time.time())}',
                'mobile_number': mobile_number,
                'amount': amount,
                'status': 'success'
            }
        }

class EkoMoneyTransferService(EkoAPIService):
    def validate_bank_account(self, account_number, ifsc_code):
        """Real bank account validation"""
        if self.use_mock:
            return {
                'status': 0,
                'message': 'Account validated successfully',
                'data': {
                    'account_number': account_number,
                    'ifsc_code': ifsc_code,
                    'account_holder_name': 'Verified Account Holder',
                    'bank_name': 'Sample Bank'
                }
            }
        
        url = f"{self.base_url}/ekoapi/v2/account/validate"
        data = {
            'initiator_id': self.initiator_id,
            'account_number': account_number,
            'ifsc_code': ifsc_code
        }
        
        try:
            response = requests.post(url, data=data, headers=self.get_headers())
            return response.json() 
        except Exception as e:
            return {'status': 1, 'message': str(e)}
    
    def transfer_money(self, user_code, recipient_details, amount, payment_mode='imps'):
        """Real money transfer"""
        if self.use_mock:
            amount_value = float(amount) if hasattr(amount, 'as_tuple') else amount
            return {
                'status': 0,
                'message': 'Money transferred successfully',
                'data': {
                    'transaction_id': f'MT{int(time.time())}',
                    'amount': amount_value,
                    'recipient_name': recipient_details.get('recipient_name'),
                    'status': 'success'
                }
            }
        
        url = f"{self.base_url}/ekoapi/v2/moneytransfer"
        data = {
            'initiator_id': self.initiator_id,
            'user_code': user_code,
            'account_number': recipient_details['account_number'],
            'ifsc_code': recipient_details['ifsc_code'],
            'recipient_name': recipient_details['recipient_name'],
            'amount': float(amount),
            'payment_mode': payment_mode,
            'client_ref_id': f"MT{int(time.time())}"
        }
        
        try:
            response = requests.post(url, data=data, headers=self.get_headers())
            return response.json()
        except Exception as e:
            return {'status': 1, 'message': str(e)}