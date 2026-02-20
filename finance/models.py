from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.urls import reverse
from students.models import Student
from accounts.models import User
import datetime

class FeeCategory(models.Model):
    """Categories of fees (e.g., Tuition, Boarding, Transport, etc.)"""
    
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=20, unique=True)
    description = models.TextField(blank=True)
    is_optional = models.BooleanField(default=False)
    is_refundable = models.BooleanField(default=False)
    
    class Meta:
        verbose_name_plural = "Fee Categories"
        ordering = ['name']
    
    def __str__(self):
        return self.name

class FeeStructure(models.Model):
    """Fee structure for different classes and terms"""
    
    TERM_CHOICES = [
        (1, 'Term 1'),
        (2, 'Term 2'),
        (3, 'Term 3'),
    ]
    
    CLASS_LEVELS = [
        (1, 'Form 1'),
        (2, 'Form 2'),
        (3, 'Form 3'),
        (4, 'Form 4'),
    ]
    
    name = models.CharField(max_length=200)
    academic_year = models.ForeignKey('academics.AcademicYear', on_delete=models.CASCADE, related_name='fee_structures')
    term = models.IntegerField(choices=TERM_CHOICES)
    class_level = models.IntegerField(choices=CLASS_LEVELS)
    
    # Fee details
    tuition_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    boarding_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    transport_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    library_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    sports_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    medical_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    development_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    other_fees = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Payment deadlines
    payment_deadline = models.DateField()
    late_payment_penalty = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Metadata
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    
    class Meta:
        ordering = ['academic_year', 'term', 'class_level']
        unique_together = ['academic_year', 'term', 'class_level']
    
    def __str__(self):
        return f"{self.academic_year} - Term {self.term} - Form {self.class_level}"
    
    def get_total_fee(self):
        """Calculate total fee amount"""
        return (self.tuition_fee + self.boarding_fee + self.transport_fee +
                self.library_fee + self.sports_fee + self.medical_fee +
                self.development_fee + self.other_fees)
    
    def get_breakdown(self):
        """Get fee breakdown as dictionary"""
        return {
            'Tuition': self.tuition_fee,
            'Boarding': self.boarding_fee,
            'Transport': self.transport_fee,
            'Library': self.library_fee,
            'Sports': self.sports_fee,
            'Medical': self.medical_fee,
            'Development': self.development_fee,
            'Other': self.other_fees,
        }

class Invoice(models.Model):
    """Invoice generated for students"""
    
    INVOICE_STATUS = [
        ('draft', 'Draft'),
        ('sent', 'Sent'),
        ('paid', 'Paid'),
        ('partially_paid', 'Partially Paid'),
        ('overdue', 'Overdue'),
        ('cancelled', 'Cancelled'),
    ]
    
    invoice_number = models.CharField(max_length=50, unique=True)
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='invoices')
    fee_structure = models.ForeignKey(FeeStructure, on_delete=models.PROTECT, related_name='invoices')
    
    # Invoice details
    issue_date = models.DateField(auto_now_add=True)
    due_date = models.DateField()
    
    # Amounts
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    discounts = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    penalties = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    balance = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Status
    status = models.CharField(max_length=20, choices=INVOICE_STATUS, default='draft')
    
    # Additional charges (JSON field for custom items)
    additional_charges = models.JSONField(default=list, blank=True)
    
    # Metadata
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    
    class Meta:
        ordering = ['-issue_date']
    
    def __str__(self):
        return f"Invoice {self.invoice_number} - {self.student.get_full_name()}"
    
    def save(self, *args, **kwargs):
        if not self.invoice_number:
            self.invoice_number = self.generate_invoice_number()
        self.balance = self.total_amount - self.amount_paid
        
        # Update status based on payment
        if self.amount_paid >= self.total_amount:
            self.status = 'paid'
        elif self.amount_paid > 0:
            self.status = 'partially_paid'
        elif self.due_date < datetime.date.today() and self.amount_paid == 0:
            self.status = 'overdue'
        
        super().save(*args, **kwargs)
    
    def generate_invoice_number(self):
        """Generate unique invoice number"""
        year = datetime.date.today().year
        last_invoice = Invoice.objects.filter(
            invoice_number__startswith=f"INV/{year}/"
        ).order_by('-id').first()
        
        if last_invoice:
            last_number = int(last_invoice.invoice_number.split('/')[-1])
            new_number = last_number + 1
        else:
            new_number = 1001
        
        return f"INV/{year}/{new_number:04d}"
    
    def get_outstanding_balance(self):
        """Get outstanding balance"""
        return self.total_amount - self.amount_paid
    
    def is_overdue(self):
        """Check if invoice is overdue"""
        return self.due_date < datetime.date.today() and self.balance > 0

class Payment(models.Model):
    """Payment records"""
    
    PAYMENT_METHODS = [
        ('cash', 'Cash'),
        ('mpesa', 'M-Pesa'),
        ('bank_transfer', 'Bank Transfer'),
        ('cheque', 'Cheque'),
        ('card', 'Credit/Debit Card'),
        ('other', 'Other'),
    ]
    
    PAYMENT_STATUS = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]
    
    transaction_id = models.CharField(max_length=100, unique=True)
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='payments')
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='payments', null=True, blank=True)
    
    # Payment details
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_date = models.DateTimeField()
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS)
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='completed')
    
    # Reference information
    reference_number = models.CharField(max_length=100, blank=True)
    mpesa_code = models.CharField(max_length=50, blank=True)
    cheque_number = models.CharField(max_length=50, blank=True)
    bank_name = models.CharField(max_length=100, blank=True)
    
    # Receipt
    receipt_number = models.CharField(max_length=50, unique=True, null=True, blank=True)
    
    # Metadata
    notes = models.TextField(blank=True)
    received_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='received_payments')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-payment_date']
    
    def __str__(self):
        return f"Payment {self.transaction_id} - {self.amount} - {self.student.get_full_name()}"
    
    def save(self, *args, **kwargs):
        if not self.transaction_id:
            self.transaction_id = self.generate_transaction_id()
        if not self.receipt_number and self.payment_status == 'completed':
            self.receipt_number = self.generate_receipt_number()
        
        super().save(*args, **kwargs)
        
        # Update invoice amount paid and balance
        if self.invoice:
            total_paid = Payment.objects.filter(
                invoice=self.invoice,
                payment_status='completed'
            ).aggregate(total=models.Sum('amount'))['total'] or 0
            
            self.invoice.amount_paid = total_paid
            self.invoice.save()
    
    def generate_transaction_id(self):
        """Generate unique transaction ID"""
        import random
        import string
        
        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        return f"TXN{timestamp}{random_str}"
    
    def generate_receipt_number(self):
        """Generate receipt number"""
        year = datetime.date.today().year
        last_receipt = Payment.objects.filter(
            receipt_number__startswith=f"RCP/{year}/"
        ).order_by('-id').first()
        
        if last_receipt:
            last_number = int(last_receipt.receipt_number.split('/')[-1])
            new_number = last_number + 1
        else:
            new_number = 1001
        
        return f"RCP/{year}/{new_number:04d}"

class ExpenseCategory(models.Model):
    """Categories for expenses"""
    
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=20, unique=True)
    description = models.TextField(blank=True)
    budget_allocation = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    class Meta:
        verbose_name_plural = "Expense Categories"
        ordering = ['name']
    
    def __str__(self):
        return self.name

class Expense(models.Model):
    """School expenses"""
    
    EXPENSE_STATUS = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('paid', 'Paid'),
    ]
    
    expense_number = models.CharField(max_length=50, unique=True)
    category = models.ForeignKey(ExpenseCategory, on_delete=models.PROTECT, related_name='expenses')
    
    # Expense details
    description = models.TextField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    expense_date = models.DateField()
    
    # Vendor information
    vendor_name = models.CharField(max_length=200)
    vendor_phone = models.CharField(max_length=15, blank=True)
    vendor_email = models.EmailField(blank=True)
    
    # Payment details
    payment_method = models.CharField(max_length=20, choices=Payment.PAYMENT_METHODS)
    payment_status = models.CharField(max_length=20, choices=EXPENSE_STATUS, default='pending')
    payment_date = models.DateField(null=True, blank=True)
    
    # Receipt/Invoice
    receipt = models.FileField(upload_to='finance/expenses/', null=True, blank=True)
    
    # Approval
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='approved_expenses')
    approved_at = models.DateTimeField(null=True, blank=True)
    
    # Metadata
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_expenses')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-expense_date']
    
    def __str__(self):
        return f"{self.expense_number} - {self.description[:50]}"
    
    def save(self, *args, **kwargs):
        if not self.expense_number:
            self.expense_number = self.generate_expense_number()
        super().save(*args, **kwargs)
    
    def generate_expense_number(self):
        """Generate unique expense number"""
        year = datetime.date.today().year
        last_expense = Expense.objects.filter(
            expense_number__startswith=f"EXP/{year}/"
        ).order_by('-id').first()
        
        if last_expense:
            last_number = int(last_expense.expense_number.split('/')[-1])
            new_number = last_number + 1
        else:
            new_number = 1001
        
        return f"EXP/{year}/{new_number:04d}"

class Budget(models.Model):
    """Annual budget for the school"""
    
    academic_year = models.ForeignKey('academics.AcademicYear', on_delete=models.CASCADE, related_name='budgets')
    category = models.ForeignKey(ExpenseCategory, on_delete=models.PROTECT, related_name='budgets')
    
    allocated_amount = models.DecimalField(max_digits=12, decimal_places=2)
    spent_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    remaining_amount = models.DecimalField(max_digits=12, decimal_places=2)
    
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['academic_year', 'category']
        ordering = ['academic_year', 'category']
    
    def __str__(self):
        return f"{self.academic_year} - {self.category.name}"
    
    def save(self, *args, **kwargs):
        self.remaining_amount = self.allocated_amount - self.spent_amount
        super().save(*args, **kwargs)
    
    def update_spent_amount(self):
        """Update spent amount from expenses"""
        total_spent = Expense.objects.filter(
            category=self.category,
            expense_date__year=self.academic_year.start_date.year,
            payment_status='paid'
        ).aggregate(total=models.Sum('amount'))['total'] or 0
        
        self.spent_amount = total_spent
        self.save()

class FeeReminder(models.Model):
    """Fee payment reminders"""
    
    REMINDER_TYPE = [
        ('email', 'Email'),
        ('sms', 'SMS'),
        ('both', 'Both'),
    ]
    
    REMINDER_STATUS = [
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('failed', 'Failed'),
    ]
    
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='fee_reminders')
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='reminders')
    
    reminder_type = models.CharField(max_length=10, choices=REMINDER_TYPE, default='sms')
    scheduled_date = models.DateField()
    sent_date = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=REMINDER_STATUS, default='pending')
    
    message = models.TextField()
    response = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-scheduled_date']
    
    def __str__(self):
        return f"Reminder for {self.student.get_full_name()} - {self.scheduled_date}"

class MpesaTransaction(models.Model):
    """M-Pesa transaction records"""
    
    TRANSACTION_TYPES = [
        ('paybill', 'Paybill'),
        ('till', 'Buy Goods Till'),
        ('stk', 'STK Push'),
    ]
    
    TRANSACTION_STATUS = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('reversed', 'Reversed'),
    ]
    
    # Transaction details
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    transaction_id = models.CharField(max_length=50, unique=True)
    transaction_date = models.DateTimeField()
    
    # Amount and phone
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    phone_number = models.CharField(max_length=15)
    
    # M-Pesa specific fields
    mpesa_receipt = models.CharField(max_length=50, unique=True)
    merchant_request_id = models.CharField(max_length=100, blank=True)
    checkout_request_id = models.CharField(max_length=100, blank=True)
    
    # Status
    status = models.CharField(max_length=20, choices=TRANSACTION_STATUS, default='pending')
    result_code = models.IntegerField(null=True, blank=True)
    result_desc = models.TextField(blank=True)
    
    # Related records
    student = models.ForeignKey(Student, on_delete=models.SET_NULL, null=True, blank=True)
    payment = models.OneToOneField(Payment, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Raw response data
    raw_response = models.JSONField(default=dict)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-transaction_date']
    
    def __str__(self):
        return f"M-Pesa: {self.mpesa_receipt} - {self.amount}"

class FinancialAid(models.Model):
    """Financial aid / bursary / scholarship records"""
    
    AID_TYPES = [
        ('scholarship', 'Scholarship'),
        ('bursary', 'Bursary'),
        ('fee_discount', 'Fee Discount'),
        ('sponsorship', 'Sponsorship'),
    ]
    
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='financial_aids')
    aid_type = models.CharField(max_length=20, choices=AID_TYPES)
    
    # Aid details
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    academic_year = models.ForeignKey('academics.AcademicYear', on_delete=models.CASCADE)
    term = models.IntegerField(choices=FeeStructure.TERM_CHOICES, null=True, blank=True)
    
    # Provider information
    provider_name = models.CharField(max_length=200)
    provider_contact = models.CharField(max_length=100, blank=True)
    reference_number = models.CharField(max_length=100, blank=True)
    
    # Dates
    awarded_date = models.DateField()
    valid_until = models.DateField(null=True, blank=True)
    
    # Status
    is_active = models.BooleanField(default=True)
    is_renewable = models.BooleanField(default=False)
    
    # Metadata
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-awarded_date']
    
    def __str__(self):
        return f"{self.get_aid_type_display()} - {self.student.get_full_name()} - {self.amount}"