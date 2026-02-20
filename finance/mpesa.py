"""
M-Pesa Integration Module
Handles all M-Pesa API interactions
"""

import requests
import json
import base64
import datetime
from decimal import Decimal
from django.conf import settings
from django.utils import timezone
from .models import MpesaTransaction, Payment

class MpesaAPI:
    """M-Pesa API wrapper"""
    
    def __init__(self, environment='sandbox'):
        self.environment = environment
        self.base_url = 'https://sandbox.safaricom.co.ke' if environment == 'sandbox' else 'https://api.safaricom.co.ke'
        
        # Get credentials from settings
        self.consumer_key = getattr(settings, 'MPESA_CONSUMER_KEY', '')
        self.consumer_secret = getattr(settings, 'MPESA_CONSUMER_SECRET', '')
        self.passkey = getattr(settings, 'MPESA_PASSKEY', '')
        self.shortcode = getattr(settings, 'MPESA_SHORTCODE', '174379')
        self.callback_url = getattr(settings, 'MPESA_CALLBACK_URL', '')
    
    def get_access_token(self):
        """Get OAuth access token"""
        url = f"{self.base_url}/oauth/v1/generate?grant_type=client_credentials"
        
        try:
            response = requests.get(
                url,
                auth=(self.consumer_key, self.consumer_secret),
                headers={'Content-Type': 'application/json'}
            )
            
            if response.status_code == 200:
                return response.json().get('access_token')
            else:
                print(f"Error getting access token: {response.text}")
                return None
        except Exception as e:
            print(f"Exception getting access token: {e}")
            return None
    
    def generate_password(self):
        """Generate password for STK push"""
        timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
        password_str = self.shortcode + self.passkey + timestamp
        password = base64.b64encode(password_str.encode()).decode('utf-8')
        return password, timestamp
    
    def stk_push(self, phone_number, amount, account_reference, transaction_desc):
        """Initiate STK push payment"""
        
        access_token = self.get_access_token()
        if not access_token:
            return {'success': False, 'error': 'Failed to get access token'}
        
        password, timestamp = self.generate_password()
        
        url = f"{self.base_url}/mpesa/stkpush/v1/processrequest"
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        # Format phone number
        if phone_number.startswith('0'):
            phone_number = '254' + phone_number[1:]
        elif phone_number.startswith('7'):
            phone_number = '254' + phone_number
        
        payload = {
            'BusinessShortCode': self.shortcode,
            'Password': password,
            'Timestamp': timestamp,
            'TransactionType': 'CustomerPayBillOnline',
            'Amount': int(amount),
            'PartyA': phone_number,
            'PartyB': self.shortcode,
            'PhoneNumber': phone_number,
            'CallBackURL': self.callback_url,
            'AccountReference': account_reference[:12],  # Max 12 chars
            'TransactionDesc': transaction_desc[:13]  # Max 13 chars
        }
        
        try:
            response = requests.post(url, json=payload, headers=headers)
            response_data = response.json()
            
            if response.status_code == 200:
                return {
                    'success': True,
                    'data': response_data,
                    'merchant_request_id': response_data.get('MerchantRequestID'),
                    'checkout_request_id': response_data.get('CheckoutRequestID'),
                    'response_code': response_data.get('ResponseCode'),
                    'response_description': response_data.get('ResponseDescription')
                }
            else:
                return {
                    'success': False,
                    'error': response_data.get('errorMessage', 'Unknown error'),
                    'data': response_data
                }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def query_status(self, checkout_request_id):
        """Query transaction status"""
        
        access_token = self.get_access_token()
        if not access_token:
            return {'success': False, 'error': 'Failed to get access token'}
        
        password, timestamp = self.generate_password()
        
        url = f"{self.base_url}/mpesa/stkpushquery/v1/query"
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            'BusinessShortCode': self.shortcode,
            'Password': password,
            'Timestamp': timestamp,
            'CheckoutRequestID': checkout_request_id
        }
        
        try:
            response = requests.post(url, json=payload, headers=headers)
            return {'success': True, 'data': response.json()}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def process_callback(self, data):
        """Process callback data from M-Pesa"""
        
        body = data.get('Body', {})
        stk_callback = body.get('stkCallback', {})
        
        result_code = stk_callback.get('ResultCode')
        result_desc = stk_callback.get('ResultDesc')
        merchant_request_id = stk_callback.get('MerchantRequestID')
        checkout_request_id = stk_callback.get('CheckoutRequestID')
        
        # Find transaction
        try:
            transaction = MpesaTransaction.objects.get(
                checkout_request_id=checkout_request_id
            )
        except MpesaTransaction.DoesNotExist:
            transaction = None
        
        if transaction:
            transaction.status = 'completed' if result_code == 0 else 'failed'
            transaction.result_code = result_code
            transaction.result_desc = result_desc
            transaction.raw_response = data
            
            if result_code == 0:
                # Extract payment details
                callback_metadata = stk_callback.get('CallbackMetadata', {})
                items = callback_metadata.get('Item', [])
                
                for item in items:
                    name = item.get('Name')
                    value = item.get('Value')
                    
                    if name == 'MpesaReceiptNumber':
                        transaction.mpesa_receipt = value
                    elif name == 'Amount':
                        transaction.amount = Decimal(str(value))
                    elif name == 'TransactionDate':
                        # Convert M-Pesa timestamp to datetime
                        date_str = str(value)
                        if len(date_str) == 14:
                            transaction.transaction_date = datetime.datetime.strptime(
                                date_str, '%Y%m%d%H%M%S'
                            )
                    elif name == 'PhoneNumber':
                        transaction.phone_number = str(value)
                
                transaction.save()
                
                # Create payment record
                if transaction.student and transaction.status == 'completed':
                    from .services import FinanceService
                    
                    payment = FinanceService.process_payment(
                        student_id=transaction.student.id,
                        amount=transaction.amount,
                        payment_method='mpesa',
                        reference=transaction.mpesa_receipt,
                        received_by=None
                    )
                    
                    transaction.payment = payment
                    transaction.save()
            else:
                transaction.save()
        
        return transaction

class B2CService:
    """Business to Customer payments"""
    
    def __init__(self, environment='sandbox'):
        self.api = MpesaAPI(environment)
    
    def send_payment(self, phone_number, amount, occasion='Salary Payment', remarks='Salary'):
        """Send B2C payment"""
        
        access_token = self.api.get_access_token()
        if not access_token:
            return {'success': False, 'error': 'Failed to get access token'}
        
        url = f"{self.api.base_url}/mpesa/b2c/v1/paymentrequest"
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        # Format phone number
        if phone_number.startswith('0'):
            phone_number = '254' + phone_number[1:]
        elif phone_number.startswith('7'):
            phone_number = '254' + phone_number
        
        payload = {
            'InitiatorName': getattr(settings, 'MPESA_INITIATOR_NAME', ''),
            'SecurityCredential': getattr(settings, 'MPESA_SECURITY_CREDENTIAL', ''),
            'CommandID': 'SalaryPayment',
            'Amount': int(amount),
            'PartyA': self.api.shortcode,
            'PartyB': phone_number,
            'Remarks': remarks[:100],
            'QueueTimeOutURL': getattr(settings, 'MPESA_TIMEOUT_URL', ''),
            'ResultURL': getattr(settings, 'MPESA_RESULT_URL', ''),
            'Occasion': occasion[:100]
        }
        
        try:
            response = requests.post(url, json=payload, headers=headers)
            return {'success': True, 'data': response.json()}
        except Exception as e:
            return {'success': False, 'error': str(e)}

class C2BService:
    """Customer to Business payments"""
    
    def __init__(self, environment='sandbox'):
        self.api = MpesaAPI(environment)
    
    def register_urls(self):
        """Register C2B URLs"""
        
        access_token = self.api.get_access_token()
        if not access_token:
            return {'success': False, 'error': 'Failed to get access token'}
        
        url = f"{self.api.base_url}/mpesa/c2b/v1/registerurl"
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            'ShortCode': self.api.shortcode,
            'ResponseType': 'Completed',
            'ConfirmationURL': getattr(settings, 'MPESA_CONFIRMATION_URL', ''),
            'ValidationURL': getattr(settings, 'MPESA_VALIDATION_URL', '')
        }
        
        try:
            response = requests.post(url, json=payload, headers=headers)
            return {'success': True, 'data': response.json()}
        except Exception as e:
            return {'success': False, 'error': str(e)}