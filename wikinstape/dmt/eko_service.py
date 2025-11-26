import requests
import hashlib
import hmac
import base64
import json
from datetime import datetime
from django.conf import settings
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)

class EkoDMTService:
    def __init__(self):
        self.base_url = getattr(settings, 'EKO_BASE_URL', 'https://api.eko.in:25002/ekoicici')
        self.developer_key = getattr(settings, 'EKO_DEVELOPER_KEY', '753595f07a59eb5a52341538fad5a63d')
        self.secret_key = getattr(settings, 'EKO_SECRET_KEY', '854313b5-a37a-445a-8bc5-a27f4f0fe56a')
        self.initiator_id = getattr(settings, 'EKO_INITIATOR_ID', '9212094999')
        self.user_code = getattr(settings, 'EKO_USER_CODE', '38130001')
    
    def generate_secret_key_hash(self, timestamp):
        """Generate secret key hash for EKO authentication"""
        try:
            message = f"{self.developer_key}{timestamp}"
            secret_bytes = bytes(self.secret_key, 'utf-8')
            message_bytes = bytes(message, 'utf-8')
            hash = hmac.new(secret_bytes, message_bytes, hashlib.sha256)
            return base64.b64encode(hash.digest()).decode()
        except Exception as e:
            logger.error(f"Error generating secret key hash: {str(e)}")
            return None
    
    def get_headers(self):
        """Generate headers for EKO API requests"""
        timestamp = str(int(timezone.now().timestamp() * 1000))
        secret_key_hash = self.generate_secret_key_hash(timestamp)
        
        return {
            'developer_key': self.developer_key,
            'secret-key': secret_key_hash,
            'secret-key-timestamp': timestamp,
            'Content-Type': 'application/x-www-form-urlencoded'
        }
    
    def check_customer(self, mobile_number):
        """
        Check if customer exists on EKO platform
        GET /customers/{customer_id_type}:{customer_id}
        """
        try:
            url = f"{self.base_url}/ekoapi/v2/customers/mobile_number:{mobile_number}"
            params = {
                'initiator_id': self.initiator_id,
                'user_code': self.user_code
            }
            
            response = requests.get(
                url, 
                params=params,
                headers=self.get_headers(),
                timeout=30
            )
            
            logger.info(f"EKO Check Customer Response: {response.status_code} - {response.text}")
            
            if response.status_code == 200:
                data = response.json()
                return {
                    'success': True,
                    'exists': data.get('status', 0) == 0,
                    'data': data.get('data', {}),
                    'message': data.get('message', '')
                }
            else:
                return {
                    'success': False,
                    'exists': False,
                    'error': f"API Error: {response.status_code}",
                    'data': {}
                }
                
        except requests.exceptions.RequestException as e:
            logger.error(f"EKO Check Customer Error: {str(e)}")
            return {
                'success': False,
                'exists': False,
                'error': f"Network error: {str(e)}",
                'data': {}
            }
        except Exception as e:
            logger.error(f"EKO Check Customer Unexpected Error: {str(e)}")
            return {
                'success': False,
                'exists': False,
                'error': f"Unexpected error: {str(e)}",
                'data': {}
            }
    
    def create_customer(self, mobile_number, name, email=""):
        """
        Create new customer on EKO platform
        PUT /customers/{customer_id_type}:{customer_id}
        """
        try:
            url = f"{self.base_url}/ekoapi/v2/customers/mobile_number:{mobile_number}"
            
            payload = {
                'initiator_id': self.initiator_id,
                'user_code': self.user_code,
                'name': name,
                'email': email,
                'mobile': mobile_number
            }
            
            response = requests.put(
                url,
                data=payload,
                headers=self.get_headers(),
                timeout=30
            )
            
            logger.info(f"EKO Create Customer Response: {response.status_code} - {response.text}")
            
            if response.status_code == 200:
                data = response.json()
                return {
                    'success': data.get('status', 1) == 0,
                    'data': data.get('data', {}),
                    'message': data.get('message', ''),
                    'customer_id': data.get('data', {}).get('customer_id')
                }
            else:
                return {
                    'success': False,
                    'error': f"API Error: {response.status_code}",
                    'data': {}
                }
                
        except Exception as e:
            logger.error(f"EKO Create Customer Error: {str(e)}")
            return {
                'success': False,
                'error': f"Error creating customer: {str(e)}",
                'data': {}
            }
    
    def verify_customer(self, mobile_number, otp):
        """
        Verify customer with OTP
        POST /customers/{customer_id_type}:{customer_id}/otp
        """
        try:
            url = f"{self.base_url}/ekoapi/v2/customers/mobile_number:{mobile_number}/otp"
            
            payload = {
                'initiator_id': self.initiator_id,
                'user_code': self.user_code,
                'otp': otp
            }
            
            response = requests.post(
                url,
                data=payload,
                headers=self.get_headers(),
                timeout=30
            )
            
            logger.info(f"EKO Verify Customer Response: {response.status_code} - {response.text}")
            
            if response.status_code == 200:
                data = response.json()
                return {
                    'success': data.get('status', 1) == 0,
                    'data': data.get('data', {}),
                    'message': data.get('message', '')
                }
            else:
                return {
                    'success': False,
                    'error': f"API Error: {response.status_code}",
                    'data': {}
                }
                
        except Exception as e:
            logger.error(f"EKO Verify Customer Error: {str(e)}")
            return {
                'success': False,
                'error': f"Error verifying customer: {str(e)}",
                'data': {}
            }
    
    def add_recipient(self, customer_mobile, recipient_data):
        """
        Add recipient for a customer
        PUT /customers/{customer_id_type}:{customer_id}/recipients/{recipients_id_type}:{id}
        """
        try:
            recipient_id = f"{recipient_data['account_number']}_{recipient_data['ifsc_code']}"
            url = f"{self.base_url}/ekoapi/v2/customers/mobile_number:{customer_mobile}/recipients/acc_ifsc:{recipient_id}"
            
            payload = {
                'initiator_id': self.initiator_id,
                'user_code': self.user_code,
                'bank_id': recipient_data['bank_id'],
                'recipient_name': recipient_data['name'],
                'recipient_mobile': recipient_data['mobile'],
                'recipient_type': 3 
            }
            
            response = requests.put(
                url,
                data=payload,
                headers=self.get_headers(),
                timeout=30
            )
            
            logger.info(f"EKO Add Recipient Response: {response.status_code} - {response.text}")
            
            if response.status_code == 200:
                data = response.json()
                return {
                    'success': data.get('status', 1) == 0,
                    'data': data.get('data', {}),
                    'message': data.get('message', ''),
                    'recipient_id': data.get('data', {}).get('recipient_id')
                }
            else:
                return {
                    'success': False,
                    'error': f"API Error: {response.status_code}",
                    'data': {}
                }
                
        except Exception as e:
            logger.error(f"EKO Add Recipient Error: {str(e)}")
            return {
                'success': False,
                'error': f"Error adding recipient: {str(e)}",
                'data': {}
            }
    
    def get_recipients(self, customer_mobile):
        """
        Get list of recipients for a customer
        GET /customers/{customer_id_type}:{customer_id}/recipients
        """
        try:
            url = f"{self.base_url}/ekoapi/v2/customers/mobile_number:{customer_mobile}/recipients"
            params = {
                'initiator_id': self.initiator_id,
                'user_code': self.user_code
            }
            
            response = requests.get(
                url,
                params=params,
                headers=self.get_headers(),
                timeout=30
            )
            
            logger.info(f"EKO Get Recipients Response: {response.status_code} - {response.text}")
            
            if response.status_code == 200:
                data = response.json()
                return {
                    'success': data.get('status', 1) == 0,
                    'data': data.get('data', {}),
                    'message': data.get('message', ''),
                    'recipients': data.get('data', {}).get('recipients', [])
                }
            else:
                return {
                    'success': False,
                    'error': f"API Error: {response.status_code}",
                    'data': {},
                    'recipients': []
                }
                
        except Exception as e:
            logger.error(f"EKO Get Recipients Error: {str(e)}")
            return {
                'success': False,
                'error': f"Error getting recipients: {str(e)}",
                'data': {},
                'recipients': []
            }
    
    def initiate_transaction(self, transaction_data):
        """
        Initiate money transfer transaction
        POST /transactions
        """
        try:
            url = f"{self.base_url}/ekoapi/v2/transactions"
            
            payload = {
                'initiator_id': self.initiator_id,
                'user_code': self.user_code,
                'customer_id': transaction_data['customer_mobile'],
                'recipient_id': transaction_data['recipient_id'],
                'amount': transaction_data['amount'],
                'channel': transaction_data['channel'],
                'state': 1, 
                'timestamp': timezone.now().strftime('%Y-%m-%d %H:%M:%S'),
                'currency': 'INR',
                'latlong': transaction_data.get('latlong', ''),
                'client_ref_id': transaction_data['client_ref_id']
            }
            
            response = requests.post(
                url,
                data=payload,
                headers=self.get_headers(),
                timeout=30
            )
            
            logger.info(f"EKO Initiate Transaction Response: {response.status_code} - {response.text}")
            
            if response.status_code == 200:
                data = response.json()
                return {
                    'success': data.get('status', 1) == 0,
                    'data': data.get('data', {}),
                    'message': data.get('message', ''),
                    'transaction_id': data.get('data', {}).get('tid'),
                    'tx_status': data.get('data', {}).get('tx_status')
                }
            else:
                return {
                    'success': False,
                    'error': f"API Error: {response.status_code}",
                    'data': {}
                }
                
        except Exception as e:
            logger.error(f"EKO Initiate Transaction Error: {str(e)}")
            return {
                'success': False,
                'error': f"Error initiating transaction: {str(e)}",
                'data': {}
            }
    
    def check_transaction_status(self, transaction_id):
        """
        Check transaction status
        GET /transactions/{id}
        """
        try:
            url = f"{self.base_url}/ekoapi/v2/transactions/{transaction_id}"
            params = {
                'initiator_id': self.initiator_id,
                'user_code': self.user_code
            }
            
            response = requests.get(
                url,
                params=params,
                headers=self.get_headers(),
                timeout=30
            )
            
            logger.info(f"EKO Check Transaction Response: {response.status_code} - {response.text}")
            
            if response.status_code == 200:
                data = response.json()
                return {
                    'success': data.get('status', 1) == 0,
                    'data': data.get('data', {}),
                    'message': data.get('message', ''),
                    'tx_status': data.get('data', {}).get('tx_status'),
                    'utr_number': data.get('data', {}).get('utrnumber')
                }
            else:
                return {
                    'success': False,
                    'error': f"API Error: {response.status_code}",
                    'data': {}
                }
                
        except Exception as e:
            logger.error(f"EKO Check Transaction Error: {str(e)}")
            return {
                'success': False,
                'error': f"Error checking transaction: {str(e)}",
                'data': {}
            }
    
    def process_refund(self, transaction_id, otp):
        """
        Process refund for failed transaction
        POST /transactions/{id}/refund
        """
        try:
            url = f"{self.base_url}/ekoapi/v2/transactions/{transaction_id}/refund"
            
            payload = {
                'initiator_id': self.initiator_id,
                'user_code': self.user_code,
                'otp': otp,
                'state': 1
            }
            
            response = requests.post(
                url,
                data=payload,
                headers=self.get_headers(),
                timeout=30
            )
            
            logger.info(f"EKO Refund Response: {response.status_code} - {response.text}")
            
            if response.status_code == 200:
                data = response.json()
                return {
                    'success': data.get('status', 1) == 0,
                    'data': data.get('data', {}),
                    'message': data.get('message', '')
                }
            else:
                return {
                    'success': False,
                    'error': f"API Error: {response.status_code}",
                    'data': {}
                }
                
        except Exception as e:
            logger.error(f"EKO Refund Error: {str(e)}")
            return {
                'success': False,
                'error': f"Error processing refund: {str(e)}",
                'data': {}
            }