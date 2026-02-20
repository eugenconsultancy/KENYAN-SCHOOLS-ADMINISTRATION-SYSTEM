"""
Services module for Finance app
Handles business logic for financial operations
"""

from django.db.models import Sum, Count, Q, Avg
from django.utils import timezone
from .models import (
    FeeStructure, Invoice, Payment, Expense, Budget,
    FinancialAid, MpesaTransaction
)
from students.models import Student
import datetime
import json
import requests
from decimal import Decimal

class FinanceService:
    """Service for finance operations"""
    
    @staticmethod
    def get_student_balance(student_id):
        """Get outstanding balance for a student"""
        invoices = Invoice.objects.filter(
            student_id=student_id,
            status__in=['sent', 'partially_paid', 'overdue']
        )
        
        total_invoiced = invoices.aggregate(total=Sum('total_amount'))['total'] or 0
        total_paid = Payment.objects.filter(
            student_id=student_id,
            payment_status='completed'
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        return total_invoiced - total_paid
    
    @staticmethod
    def generate_invoice(student, fee_structure, due_date, created_by, discounts=0, penalties=0):
        """Generate a single invoice for a student"""
        
        # Check if invoice already exists
        if Invoice.objects.filter(student=student, fee_structure=fee_structure).exists():
            return None
        
        # Calculate amounts
        subtotal = fee_structure.get_total_fee()
        total_amount = subtotal - discounts + penalties
        
        # Create invoice
        invoice = Invoice.objects.create(
            student=student,
            fee_structure=fee_structure,
            due_date=due_date,
            subtotal=subtotal,
            discounts=discounts,
            penalties=penalties,
            total_amount=total_amount,
            balance=total_amount,
            status='sent',
            created_by=created_by
        )
        
        return invoice
    
    @staticmethod
    def generate_bulk_invoices(students, academic_year, term, due_date, created_by):
        """Generate invoices for multiple students"""
        
        generated = 0
        skipped = 0
        
        for student in students:
            # Get fee structure for this student's class
            fee_structure = FeeStructure.objects.filter(
                academic_year=academic_year,
                term=term,
                class_level=student.current_class,
                is_active=True
            ).first()
            
            if fee_structure:
                invoice = FinanceService.generate_invoice(
                    student=student,
                    fee_structure=fee_structure,
                    due_date=due_date,
                    created_by=created_by
                )
                
                if invoice:
                    generated += 1
                else:
                    skipped += 1
            else:
                skipped += 1
        
        return {
            'generated': generated,
            'skipped': skipped
        }
    
    @staticmethod
    def process_payment(student_id, amount, payment_method, reference, received_by, invoice_id=None):
        """Process a payment"""
        
        # Create payment record
        payment = Payment.objects.create(
            student_id=student_id,
            invoice_id=invoice_id,
            amount=amount,
            payment_date=timezone.now(),
            payment_method=payment_method,
            payment_status='completed',
            reference_number=reference,
            received_by=received_by
        )
        
        # Update invoice if specified
        if invoice_id:
            invoice = Invoice.objects.get(id=invoice_id)
            total_paid = Payment.objects.filter(
                invoice=invoice,
                payment_status='completed'
            ).aggregate(total=Sum('amount'))['total'] or 0
            
            invoice.amount_paid = total_paid
            invoice.balance = invoice.total_amount - total_paid
            
            if invoice.balance <= 0:
                invoice.status = 'paid'
            elif total_paid > 0:
                invoice.status = 'partially_paid'
            
            invoice.save()
        
        return payment
    
    @staticmethod
    def get_monthly_collection_data(year=None):
        """Get monthly collection data for charts"""
        if not year:
            year = timezone.now().year
        
        monthly_data = []
        
        for month in range(1, 13):
            total = Payment.objects.filter(
                payment_status='completed',
                payment_date__year=year,
                payment_date__month=month
            ).aggregate(total=Sum('amount'))['total'] or 0
            
            monthly_data.append({
                'month': month,
                'total': float(total)
            })
        
        return monthly_data
    
    @staticmethod
    def get_outstanding_summary():
        """Get summary of outstanding fees"""
        
        # By class
        by_class = []
        for class_level in range(1, 5):
            students = Student.objects.filter(current_class=class_level, is_active=True)
            total_outstanding = 0
            
            for student in students:
                total_outstanding += FinanceService.get_student_balance(student.id)
            
            by_class.append({
                'class': f'Form {class_level}',
                'outstanding': float(total_outstanding)
            })
        
        # Overall
        total_outstanding = sum(item['outstanding'] for item in by_class)
        
        return {
            'by_class': by_class,
            'total': total_outstanding
        }
    
    @staticmethod
    def apply_financial_aid(student_id, aid_id):
        """Apply financial aid to student's invoices"""
        aid = FinancialAid.objects.get(id=aid_id)
        
        # Get unpaid invoices for the term
        invoices = Invoice.objects.filter(
            student_id=student_id,
            fee_structure__term=aid.term if aid.term else None,
            status__in=['sent', 'partially_paid']
        )
        
        remaining_aid = aid.amount
        
        for invoice in invoices.order_by('due_date'):
            if remaining_aid <= 0:
                break
            
            outstanding = invoice.balance
            
            if outstanding > 0:
                # Apply aid to this invoice
                apply_amount = min(remaining_aid, outstanding)
                
                # Create payment record for aid
                Payment.objects.create(
                    student_id=student_id,
                    invoice=invoice,
                    amount=apply_amount,
                    payment_date=timezone.now(),
                    payment_method='other',
                    payment_status='completed',
                    reference_number=f"AID-{aid.id}",
                    notes=f"Financial aid from {aid.provider_name}"
                )
                
                remaining_aid -= apply_amount
        
        return remaining_aid

class ReportService:
    """Service for generating financial reports"""
    
    @staticmethod
    def get_collection_report(start_date, end_date):
        """Generate collection report for date range"""
        
        payments = Payment.objects.filter(
            payment_status='completed',
            payment_date__date__gte=start_date,
            payment_date__date__lte=end_date
        ).select_related('student', 'invoice')
        
        # Summary
        total_collected = payments.aggregate(total=Sum('amount'))['total'] or 0
        total_transactions = payments.count()
        
        # By payment method
        by_method = payments.values('payment_method').annotate(
            total=Sum('amount'),
            count=Count('id')
        ).order_by('-total')
        
        # Daily breakdown
        daily = payments.extra(
            {'day': "date(payment_date)"}
        ).values('day').annotate(
            total=Sum('amount'),
            count=Count('id')
        ).order_by('day')
        
        return {
            'start_date': start_date,
            'end_date': end_date,
            'total_collected': total_collected,
            'total_transactions': total_transactions,
            'average_transaction': total_collected / total_transactions if total_transactions > 0 else 0,
            'by_method': by_method,
            'daily': daily,
            'payments': payments[:100]  # Limit to 100 for display
        }
    
    @staticmethod
    def get_outstanding_report():
        """Generate outstanding fees report"""
        
        invoices = Invoice.objects.filter(
            status__in=['sent', 'partially_paid', 'overdue'],
            balance__gt=0
        ).select_related('student', 'fee_structure').order_by('-balance')
        
        total_outstanding = invoices.aggregate(total=Sum('balance'))['total'] or 0
        
        # By class
        by_class = []
        for class_level in range(1, 5):
            class_invoices = invoices.filter(student__current_class=class_level)
            total = class_invoices.aggregate(total=Sum('balance'))['total'] or 0
            count = class_invoices.count()
            
            by_class.append({
                'class': f'Form {class_level}',
                'total': total,
                'count': count
            })
        
        # Overdue summary
        overdue = invoices.filter(due_date__lt=timezone.now().date())
        total_overdue = overdue.aggregate(total=Sum('balance'))['total'] or 0
        overdue_count = overdue.count()
        
        return {
            'total_outstanding': total_outstanding,
            'total_invoices': invoices.count(),
            'by_class': by_class,
            'overdue_total': total_overdue,
            'overdue_count': overdue_count,
            'invoices': invoices[:100]  # Top 100 defaulters
        }
    
    @staticmethod
    def get_expense_report(start_date, end_date):
        """Generate expense report for date range"""
        
        expenses = Expense.objects.filter(
            payment_status='paid',
            expense_date__gte=start_date,
            expense_date__lte=end_date
        ).select_related('category')
        
        total_expenses = expenses.aggregate(total=Sum('amount'))['total'] or 0
        
        # By category
        by_category = expenses.values(
            'category__name', 'category__id'
        ).annotate(
            total=Sum('amount'),
            count=Count('id')
        ).order_by('-total')
        
        # Monthly breakdown
        monthly = expenses.extra(
            {'month': "strftime('%%Y-%%m', expense_date)"}
        ).values('month').annotate(
            total=Sum('amount'),
            count=Count('id')
        ).order_by('month')
        
        return {
            'start_date': start_date,
            'end_date': end_date,
            'total_expenses': total_expenses,
            'total_transactions': expenses.count(),
            'by_category': by_category,
            'monthly': monthly,
            'expenses': expenses[:100]
        }
    
    @staticmethod
    def get_student_statement(student):
        """Generate fee statement for a student"""
        
        invoices = Invoice.objects.filter(student=student).order_by('issue_date')
        payments = Payment.objects.filter(
            student=student,
            payment_status='completed'
        ).order_by('payment_date')
        
        # Calculate running balance
        transactions = []
        running_balance = 0
        
        # Add invoices (debits)
        for invoice in invoices:
            running_balance += invoice.total_amount
            transactions.append({
                'date': invoice.issue_date,
                'description': f"Invoice: {invoice.invoice_number} - {invoice.fee_structure}",
                'debit': invoice.total_amount,
                'credit': 0,
                'balance': running_balance
            })
        
        # Add payments (credits)
        for payment in payments:
            running_balance -= payment.amount
            transactions.append({
                'date': payment.payment_date.date(),
                'description': f"Payment: {payment.transaction_id} ({payment.get_payment_method_display()})",
                'debit': 0,
                'credit': payment.amount,
                'balance': running_balance
            })
        
        # Sort by date
        transactions.sort(key=lambda x: x['date'])
        
        # Recalculate running balance
        balance = 0
        for trans in transactions:
            balance += trans['debit'] - trans['credit']
            trans['balance'] = balance
        
        return {
            'student': student,
            'transactions': transactions,
            'total_invoiced': sum(t['debit'] for t in transactions),
            'total_paid': sum(t['credit'] for t in transactions),
            'current_balance': balance
        }

class MpesaService:
    """Service for M-Pesa integration"""
    
    # Safaricom API endpoints
    API_URLS = {
        'sandbox': 'https://sandbox.safaricom.co.ke',
        'production': 'https://api.safaricom.co.ke'
    }
    
    @staticmethod
    def get_access_token(consumer_key, consumer_secret, environment='sandbox'):
        """Get OAuth access token from Safaricom"""
        
        api_url = MpesaService.API_URLS[environment]
        url = f"{api_url}/oauth/v1/generate?grant_type=client_credentials"
        
        try:
            response = requests.get(
                url,
                auth=(consumer_key, consumer_secret),
                headers={'Content-Type': 'application/json'}
            )
            
            if response.status_code == 200:
                return response.json().get('access_token')
            else:
                return None
        except Exception as e:
            print(f"Error getting access token: {e}")
            return None
    
    @staticmethod
    def initiate_stk_push(phone_number, amount, student=None, invoice=None):
        """Initiate STK push payment"""
        
        # This would contain your actual M-Pesa API credentials
        # Store these in environment variables
        business_short_code = '174379'  # Test shortcode
        passkey = 'your_passkey'
        callback_url = 'https://your-domain.com/finance/payments/mpesa/callback/'
        
        # Format phone number
        if phone_number.startswith('0'):
            phone_number = '254' + phone_number[1:]
        elif phone_number.startswith('7'):
            phone_number = '254' + phone_number
        
        # Generate timestamp
        import datetime
        timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
        
        # Generate password
        import base64
        password_str = business_short_code + passkey + timestamp
        password = base64.b64encode(password_str.encode()).decode('utf-8')
        
        # Prepare request data
        data = {
            'BusinessShortCode': business_short_code,
            'Password': password,
            'Timestamp': timestamp,
            'TransactionType': 'CustomerPayBillOnline',
            'Amount': int(amount),
            'PartyA': phone_number,
            'PartyB': business_short_code,
            'PhoneNumber': phone_number,
            'CallBackURL': callback_url,
            'AccountReference': f"STD-{student.admission_number if student else 'PAY'}",
            'TransactionDesc': 'School Fees Payment'
        }
        
        # Make API request (simplified - you'd need actual implementation)
        # This is a placeholder for the actual API call
        
        # Create transaction record
        transaction = MpesaTransaction.objects.create(
            transaction_type='stk',
            transaction_id=f"TXN{timestamp}",
            transaction_date=timezone.now(),
            amount=amount,
            phone_number=phone_number,
            mpesa_receipt='',
            merchant_request_id='',
            checkout_request_id='',
            status='pending',
            student=student
        )
        
        # Return response
        return {
            'success': True,
            'transaction': transaction,
            'message': 'STK push initiated. Please check your phone.'
        }
    
    @staticmethod
    def process_callback(data):
        """Process M-Pesa callback"""
        
        # Extract callback data
        body = data.get('Body', {})
        stk_callback = body.get('stkCallback', {})
        
        checkout_request_id = stk_callback.get('CheckoutRequestID')
        result_code = stk_callback.get('ResultCode')
        result_desc = stk_callback.get('ResultDesc')
        
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
                    if item.get('Name') == 'MpesaReceiptNumber':
                        transaction.mpesa_receipt = item.get('Value')
                    elif item.get('Name') == 'Amount':
                        transaction.amount = item.get('Value')
                    elif item.get('Name') == 'TransactionDate':
                        transaction.transaction_date = item.get('Value')
                    elif item.get('Name') == 'PhoneNumber':
                        transaction.phone_number = item.get('Value')
                
                transaction.save()
                
                # Create payment record if transaction successful
                if transaction.student:
                    FinanceService.process_payment(
                        student_id=transaction.student.id,
                        amount=transaction.amount,
                        payment_method='mpesa',
                        reference=transaction.mpesa_receipt,
                        received_by=None  # System user
                    )
                    
                    # Link payment to transaction
                    transaction.payment = Payment.objects.filter(
                        reference_number=transaction.mpesa_receipt
                    ).first()
                    transaction.save()
            else:
                transaction.save()
        
        return transaction