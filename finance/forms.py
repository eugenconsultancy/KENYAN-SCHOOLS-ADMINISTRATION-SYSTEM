from django import forms
from django.core.exceptions import ValidationError
from .models import (
    FeeCategory, FeeStructure, Invoice, Payment, ExpenseCategory,
    Expense, Budget, FeeReminder, FinancialAid, MpesaTransaction
)
from students.models import Student
from academics.models import AcademicYear
import datetime

class FeeCategoryForm(forms.ModelForm):
    """Form for fee categories"""
    
    class Meta:
        model = FeeCategory
        fields = ['name', 'code', 'description', 'is_optional', 'is_refundable']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }

class FeeStructureForm(forms.ModelForm):
    """Form for fee structure"""
    
    class Meta:
        model = FeeStructure
        fields = [
            'name', 'academic_year', 'term', 'class_level',
            'tuition_fee', 'boarding_fee', 'transport_fee',
            'library_fee', 'sports_fee', 'medical_fee',
            'development_fee', 'other_fees', 'payment_deadline',
            'late_payment_penalty', 'is_active'
        ]
        widgets = {
            'payment_deadline': forms.DateInput(attrs={'type': 'date'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set default values
        for field in ['tuition_fee', 'boarding_fee', 'transport_fee', 
                     'library_fee', 'sports_fee', 'medical_fee',
                     'development_fee', 'other_fees', 'late_payment_penalty']:
            self.fields[field].initial = 0
            self.fields[field].widget.attrs['class'] = 'fee-amount'
    
    def clean(self):
        cleaned_data = super().clean()
        total = sum([
            cleaned_data.get('tuition_fee', 0),
            cleaned_data.get('boarding_fee', 0),
            cleaned_data.get('transport_fee', 0),
            cleaned_data.get('library_fee', 0),
            cleaned_data.get('sports_fee', 0),
            cleaned_data.get('medical_fee', 0),
            cleaned_data.get('development_fee', 0),
            cleaned_data.get('other_fees', 0),
        ])
        
        if total <= 0:
            raise ValidationError('Total fee amount must be greater than zero.')
        
        return cleaned_data

class InvoiceForm(forms.ModelForm):
    """Form for creating/editing invoices"""
    
    class Meta:
        model = Invoice
        fields = [
            'student', 'fee_structure', 'due_date',
            'discounts', 'penalties', 'additional_charges', 'notes'
        ]
        widgets = {
            'due_date': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 3}),
            'additional_charges': forms.HiddenInput(),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['student'].queryset = Student.objects.filter(is_active=True)
        self.fields['fee_structure'].queryset = FeeStructure.objects.filter(is_active=True)
        self.fields['notes'].required = False
        self.fields['additional_charges'].required = False
        
        # Calculate total if editing
        if self.instance.pk:
            self.fields['subtotal'] = forms.DecimalField(
                initial=self.instance.subtotal,
                disabled=True,
                required=False
            )
            self.fields['total_amount'] = forms.DecimalField(
                initial=self.instance.total_amount,
                disabled=True,
                required=False
            )
    
    def clean(self):
        cleaned_data = super().clean()
        student = cleaned_data.get('student')
        fee_structure = cleaned_data.get('fee_structure')
        
        # Check if invoice already exists for this student and fee structure
        if student and fee_structure:
            if Invoice.objects.filter(
                student=student,
                fee_structure=fee_structure
            ).exclude(pk=self.instance.pk).exists():
                raise ValidationError(
                    f'An invoice already exists for {student.get_full_name()} '
                    f'for {fee_structure}'
                )
        
        return cleaned_data

class InvoiceGenerationForm(forms.Form):
    """Form for bulk invoice generation"""
    
    academic_year = forms.ModelChoiceField(
        queryset=AcademicYear.objects.all(),
        required=True
    )
    term = forms.ChoiceField(choices=FeeStructure.TERM_CHOICES)
    class_level = forms.ChoiceField(choices=FeeStructure.CLASS_LEVELS, required=False)
    stream = forms.ChoiceField(choices=Student.STREAMS, required=False)
    due_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    
    def generate_invoices(self, created_by):
        """Generate invoices for selected students"""
        from .services import FinanceService
        
        students = Student.objects.filter(is_active=True)
        
        if self.cleaned_data['class_level']:
            students = students.filter(current_class=self.cleaned_data['class_level'])
        if self.cleaned_data['stream']:
            students = students.filter(stream=self.cleaned_data['stream'])
        
        results = FinanceService.generate_bulk_invoices(
            students=students,
            academic_year=self.cleaned_data['academic_year'],
            term=int(self.cleaned_data['term']),
            due_date=self.cleaned_data['due_date'],
            created_by=created_by
        )
        
        return results

class PaymentForm(forms.ModelForm):
    """Form for recording payments"""
    
    class Meta:
        model = Payment
        fields = [
            'student', 'invoice', 'amount', 'payment_date',
            'payment_method', 'reference_number', 'mpesa_code',
            'cheque_number', 'bank_name', 'notes'
        ]
        widgets = {
            'payment_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['student'].queryset = Student.objects.filter(is_active=True)
        self.fields['invoice'].required = False
        self.fields['invoice'].queryset = Invoice.objects.filter(
            status__in=['draft', 'sent', 'partially_paid', 'overdue']
        )
        self.fields['reference_number'].required = False
        self.fields['mpesa_code'].required = False
        self.fields['cheque_number'].required = False
        self.fields['bank_name'].required = False
        self.fields['notes'].required = False
        
        # Set initial payment date
        self.fields['payment_date'].initial = datetime.datetime.now()
    
    def clean(self):
        cleaned_data = super().clean()
        amount = cleaned_data.get('amount')
        invoice = cleaned_data.get('invoice')
        
        if invoice and amount:
            outstanding = invoice.get_outstanding_balance()
            if amount > outstanding:
                raise ValidationError(
                    f'Payment amount ({amount}) cannot exceed outstanding balance ({outstanding})'
                )
        
        return cleaned_data

class MpesaPaymentForm(forms.Form):
    """Form for M-Pesa STK Push payment"""
    
    phone_number = forms.CharField(
        max_length=15,
        help_text='Enter phone number in format 2547XXXXXXXX'
    )
    amount = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=10,
        max_value=150000
    )
    student = forms.ModelChoiceField(
        queryset=Student.objects.filter(is_active=True),
        required=True
    )
    invoice = forms.ModelChoiceField(
        queryset=Invoice.objects.filter(status__in=['sent', 'partially_paid', 'overdue']),
        required=False
    )
    
    def clean_phone_number(self):
        phone = self.cleaned_data['phone_number']
        # Basic phone validation for Kenya
        if not phone.startswith('254') or len(phone) != 12:
            raise ValidationError('Phone number must be in format 2547XXXXXXXX')
        return phone

class ExpenseCategoryForm(forms.ModelForm):
    """Form for expense categories"""
    
    class Meta:
        model = ExpenseCategory
        fields = ['name', 'code', 'description', 'budget_allocation']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }

class ExpenseForm(forms.ModelForm):
    """Form for recording expenses"""
    
    class Meta:
        model = Expense
        fields = [
            'category', 'description', 'amount', 'expense_date',
            'vendor_name', 'vendor_phone', 'vendor_email',
            'payment_method', 'receipt', 'notes'
        ]
        widgets = {
            'expense_date': forms.DateInput(attrs={'type': 'date'}),
            'description': forms.Textarea(attrs={'rows': 3}),
            'notes': forms.Textarea(attrs={'rows': 2}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['vendor_phone'].required = False
        self.fields['vendor_email'].required = False
        self.fields['receipt'].required = False
        self.fields['notes'].required = False
        self.fields['expense_date'].initial = datetime.date.today()

class BudgetForm(forms.ModelForm):
    """Form for budget allocation"""
    
    class Meta:
        model = Budget
        fields = ['academic_year', 'category', 'allocated_amount', 'notes']
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['notes'].required = False

class FeeReminderForm(forms.ModelForm):
    """Form for fee reminders"""
    
    class Meta:
        model = FeeReminder
        fields = ['student', 'invoice', 'reminder_type', 'scheduled_date', 'message']
        widgets = {
            'scheduled_date': forms.DateInput(attrs={'type': 'date'}),
            'message': forms.Textarea(attrs={'rows': 4}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['student'].queryset = Student.objects.filter(is_active=True)
        self.fields['invoice'].queryset = Invoice.objects.filter(
            status__in=['sent', 'partially_paid', 'overdue']
        )

class FinancialAidForm(forms.ModelForm):
    """Form for financial aid records"""
    
    class Meta:
        model = FinancialAid
        fields = [
            'student', 'aid_type', 'amount', 'academic_year',
            'term', 'provider_name', 'provider_contact',
            'reference_number', 'awarded_date', 'valid_until',
            'is_renewable', 'notes'
        ]
        widgets = {
            'awarded_date': forms.DateInput(attrs={'type': 'date'}),
            'valid_until': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['term'].required = False
        self.fields['provider_contact'].required = False
        self.fields['reference_number'].required = False
        self.fields['valid_until'].required = False
        self.fields['notes'].required = False
        self.fields['awarded_date'].initial = datetime.date.today()

class DateRangeForm(forms.Form):
    """Form for date range selection in reports"""
    
    start_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        required=True
    )
    end_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        required=True
    )
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        
        if start_date and end_date and end_date < start_date:
            raise ValidationError('End date cannot be before start date.')
        
        return cleaned_data

class FeeSearchForm(forms.Form):
    """Form for searching fee records"""
    
    query = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'Search by student name or admission number...'})
    )
    academic_year = forms.ModelChoiceField(
        queryset=AcademicYear.objects.all(),
        required=False
    )
    term = forms.ChoiceField(
        choices=[('', 'All Terms')] + list(FeeStructure.TERM_CHOICES),
        required=False
    )
    class_level = forms.ChoiceField(
        choices=[('', 'All Classes')] + list(FeeStructure.CLASS_LEVELS),
        required=False
    )
    status = forms.ChoiceField(
        choices=[('', 'All Statuses')] + list(Invoice.INVOICE_STATUS),
        required=False
    )