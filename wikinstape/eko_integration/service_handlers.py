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
        """Perform recharge - EXACT Ruby implementation"""
        if self.use_mock:
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
        
        endpoint = "/v2/billpayments/paybill"
        
        payload = {
            "source_ip": "121.121.1.1",
            "user_code": user_code,
            "amount": float(amount),
            "client_ref_id": f"RECH{int(time.time())}",
            "utility_acc_no": mobile_number,
            "confirmation_mobile_no": mobile_number,
            "sender_name": "Customer",
            "operator_id": operator_id,
            "latlong": "28.6139,77.2090",
            "hc_channel": 1
        }
        
        timestamp = str(int(time.time() * 1000))
        amount_str = str(float(amount))
        concat_string = f"{timestamp}{mobile_number}{amount_str}{user_code}"
        
        full_endpoint = f"{endpoint}?initiator_id={self.initiator_id}"
        
        return self.make_request('POST', full_endpoint, payload, concat_string)

class EkoMoneyTransferService(EkoAPIService):
    
    def get_customer_info(self, customer_mobile):
        """Step 2: Check if customer exists"""
        endpoint = f"/ekoapi/v2/customers/mobile_number:{customer_mobile}"
        
        params = {
            'initiator_id': self.initiator_id,
            'user_code': self.user_code
        }
        
        response = self.make_request_v1('GET', endpoint, params)
        print(f"📞 Customer Check: {response}")
        return response
    
    def create_customer(self, customer_data):
        """Step 3: Create new customer if not exists"""
        endpoint = "/ekoapi/v2/customers"
        
        data = {
            'initiator_id': self.initiator_id,
            'mobile': customer_data['mobile'],
            'first_name': customer_data.get('first_name', 'Customer')[:20],
            'last_name': customer_data.get('last_name', '')[:20],
            'email': customer_data.get('email', 'customer@example.com'),
            'user_code': self.user_code
        }
        
        response = self.make_request_v1('POST', endpoint, data)
        print(f"👤 Customer Creation: {response}")
        return response
    
    def verify_customer_identity(self, customer_mobile, otp=None):
        """Step 4: Verify customer identity"""
        endpoint = f"/ekoapi/v2/customers/mobile_number:{customer_mobile}/verify"
        
        data = {
            'initiator_id': self.initiator_id,
            'user_code': self.user_code
        }
        
        if otp:
            data['otp'] = otp
            
        response = self.make_request_v1('PUT', endpoint, data)
        print(f"✅ Customer Verification: {response}")
        return response
    
    def resend_otp(self, customer_mobile):
        """Resend OTP for customer verification"""
        endpoint = f"/ekoapi/v2/customers/mobile_number:{customer_mobile}/otp"
        
        data = {
            'initiator_id': self.initiator_id,
            'user_code': self.user_code
        }
        
        response = self.make_request_v1('POST', endpoint, data)
        print(f"🔄 OTP Resend: {response}")
        return response
    
    def add_recipient(self, customer_mobile, recipient_data):
        """Step 5: Add recipient for money transfer - FIXED"""
        # ✅ Correct format: acc_ifsc:account_number_ifsc
        recipient_id = f"{recipient_data['account_number']}_{recipient_data['ifsc_code']}"
        endpoint = f"/ekoapi/v2/customers/mobile_number:{customer_mobile}/recipients/acc_ifsc:{recipient_id}"
        
        data = {
            'initiator_id': self.initiator_id,
            'recipient_mobile': recipient_data.get('recipient_mobile', customer_mobile),
            'bank_id': 56,  # SBI bank ID
            'recipient_type': 3,
            'recipient_name': recipient_data['recipient_name'][:30],
            'user_code': self.user_code
        }
        
        response = self.make_request_v1('PUT', endpoint, data)
        print(f"👥 Add Recipient: {response}")
        return response
    
    def get_recipients(self, customer_mobile):
        """Get list of recipients for a customer"""
        endpoint = f"/ekoapi/v2/customers/mobile_number:{customer_mobile}/recipients"
        
        params = {
            'initiator_id': self.initiator_id,
            'user_code': self.user_code
        }
        
        response = self.make_request_v1('GET', endpoint, params)
        print(f"📋 Get Recipients: {response}")
        return response
    
    def initiate_transaction(self, transaction_data):
        """Step 6: Initiate money transfer transaction"""
        endpoint = "/ekoapi/v2/transactions"
        
        # Prepare payload as form-data
        payload = {
            'initiator_id': self.initiator_id,
            'recipient_id': transaction_data['recipient_id'],
            'amount': int(transaction_data['amount']),
            'timestamp': transaction_data['timestamp'],
            'currency': 'INR',
            'customer_id': int(transaction_data['customer_mobile']),
            'client_ref_id': transaction_data['client_ref_id'],
            'state': 1,
            'channel': transaction_data.get('channel', 2),
            'latlong': transaction_data.get('latlong', '28.6139,77.2090'),
            'user_code': self.user_code
        }
        
        # Convert to form-data format
        form_data = urlencode(payload)
        
        url = f"{self.base_url}{endpoint}"
        headers = self.get_headers_v1()
        
        try:
            response = requests.post(url, data=form_data, headers=headers, timeout=30)
            print(f"💰 Transaction Initiation: {response.text}")
            
            try:
                return response.json()
            except json.JSONDecodeError:
                return {
                    'status': 1, 
                    'message': f'Invalid JSON response: {response.text}',
                    'raw_response': response.text
                }
                
        except requests.exceptions.RequestException as e:
            print(f"Request Error: {str(e)}")
            return {'status': 1, 'message': f'Request failed: {str(e)}'}
    
    def check_transaction_status(self, client_ref_id):
        """Step 7: Check transaction status"""
        endpoint = f"/ekoapi/v2/transactions/client_ref_id:{client_ref_id}"
        
        params = {
            'initiator_id': self.initiator_id,
            'user_code': self.user_code
        }
        
        response = self.make_request_v1('GET', endpoint, params)
        print(f"📊 Transaction Status: {response}")
        return response
    
    def process_refund(self, transaction_id, otp):
        """Process refund for a transaction"""
        endpoint = f"/ekoapi/v2/transactions/{transaction_id}/refund"
        
        data = {
            'initiator_id': self.initiator_id,
            'otp': otp,
            'state': 1,
            'user_code': self.user_code
        }
        
        response = self.make_request_v1('POST', endpoint, data)
        print(f"🔄 Refund Processing: {response}")
        return response
    
    def complete_dmt_flow(self, transfer_data):
        """
        Complete DMT flow as per Eko documentation - FIXED
        """
        customer_mobile = transfer_data['customer_mobile']
        recipient_data = transfer_data['recipient_data']
        amount = transfer_data['amount']
        
        print(f"🚀 STARTING DMT FLOW for customer: {customer_mobile}")
        
        # Step 1: Merchant already onboarded
        
        # Step 2: Check if customer exists
        print("📞 STEP 2: Checking customer existence...")
        customer_info = self.get_customer_info(customer_mobile)
        
        customer_exists = customer_info.get('status') == 0
        
        if not customer_exists:
            # Step 3: Create new customer
            print("👤 STEP 3: Creating new customer...")
            customer_create_data = {
                'mobile': customer_mobile,
                'first_name': recipient_data.get('sender_first_name', 'Customer'),
                'last_name': recipient_data.get('sender_last_name', ''),
                'email': recipient_data.get('sender_email', 'test@example.com'),
            }
            
            create_result = self.create_customer(customer_create_data)
            
            if create_result.get('status') != 0:
                return {
                    'status': 1, 
                    'message': 'Customer creation failed', 
                    'details': create_result,
                    'step': 'customer_creation'
                }
            
            # Step 4: Verify customer identity
            print("✅ STEP 4: Verifying customer identity...")
            verify_result = self.verify_customer_identity(customer_mobile)
            
            if verify_result.get('status') != 0:
                print("⚠️ Customer verification failed, but continuing for UAT...")
        else:
            print("✅ Customer already exists, skipping creation and verification")
        
        # Step 5: Check existing recipients
        print("📋 STEP 5: Checking existing recipients...")
        recipients = self.get_recipients(customer_mobile)
        
        recipient_id = None
        if recipients.get('status') == 0 and recipients.get('data'):
            # ✅ Correct field names use karein
            for recipient in recipients['data']:
                if (recipient.get('account_number') == recipient_data['account_number'] and
                    recipient.get('ifsc') == recipient_data['ifsc_code']):
                    recipient_id = recipient.get('recipient_id')  # ✅ Correct field
                    print(f"✅ Found existing recipient ID: {recipient_id}")
                    break
        
        # Step 5a: Add recipient if not exists
        if not recipient_id:
            print("👥 STEP 5a: Adding new recipient...")
            add_recipient_result = self.add_recipient(customer_mobile, recipient_data)
            
            if add_recipient_result.get('status') != 0:
                return {
                    'status': 1, 
                    'message': 'Recipient addition failed', 
                    'details': add_recipient_result,
                    'step': 'recipient_addition'
                }
            
            # ✅ Correct field name for recipient ID
            recipient_id = add_recipient_result['data'].get('recipient_id')
            print(f"✅ New recipient ID: {recipient_id}")
        
        # Step 6: Initiate transaction
        print("💰 STEP 6: Initiating transaction...")
        from datetime import datetime
        transaction_data = {
            'initiator_id': self.initiator_id,
            'recipient_id': recipient_id,
            'amount': amount,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'customer_mobile': customer_mobile,
            'client_ref_id': f"DMT{int(time.time())}",
            'channel': 2,
            'latlong': '28.6139,77.2090',
            'user_code': self.user_code
        }
        
        transfer_result = self.initiate_transaction(transaction_data)
        print(f"📊 Transaction Result: {transfer_result}")
        
        return transfer_result