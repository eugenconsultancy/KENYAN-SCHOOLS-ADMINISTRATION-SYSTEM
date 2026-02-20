from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import (
    FeeCategory, FeeStructure, Invoice, Payment, ExpenseCategory,
    Expense, Budget, FeeReminder, FinancialAid, MpesaTransaction
)

class FeeStructureInline(admin.TabularInline):
    model = FeeStructure
    extra = 0
    fields = ['term', 'class_level', 'get_total_fee', 'is_active']
    readonly_fields = ['get_total_fee']

@admin.register(FeeCategory)
class FeeCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'is_optional', 'is_refundable']
    list_filter = ['is_optional', 'is_refundable']
    search_fields = ['name', 'code']

@admin.register(FeeStructure)
class FeeStructureAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'academic_year', 'get_term_display', 'get_class_level_display',
        'get_total_fee', 'payment_deadline', 'is_active'
    ]
    list_filter = ['academic_year', 'term', 'class_level', 'is_active']
    search_fields = ['name']
    date_hierarchy = 'payment_deadline'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'academic_year', 'term', 'class_level', 'is_active')
        }),
        ('Fee Breakdown', {
            'fields': (
                'tuition_fee', 'boarding_fee', 'transport_fee',
                'library_fee', 'sports_fee', 'medical_fee',
                'development_fee', 'other_fees'
            )
        }),
        ('Payment Terms', {
            'fields': ('payment_deadline', 'late_payment_penalty')
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at']
    
    def get_total_fee(self, obj):
        return format_html('<strong>KSh {}</strong>', obj.get_total_fee())
    get_total_fee.short_description = 'Total Fee'

class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0
    fields = ['transaction_id', 'amount', 'payment_date', 'payment_method', 'payment_status']
    readonly_fields = ['transaction_id']

@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = [
        'invoice_number', 'student', 'fee_structure', 'total_amount',
        'amount_paid', 'balance', 'status', 'due_date', 'is_overdue'
    ]
    list_filter = ['status', 'issue_date', 'due_date']
    search_fields = ['invoice_number', 'student__user__first_name', 'student__admission_number']
    date_hierarchy = 'issue_date'
    raw_id_fields = ['student', 'created_by']
    readonly_fields = ['invoice_number', 'balance', 'created_at', 'updated_at']
    inlines = [PaymentInline]
    
    fieldsets = (
        ('Invoice Information', {
            'fields': ('invoice_number', 'student', 'fee_structure', 'status')
        }),
        ('Dates', {
            'fields': ('issue_date', 'due_date')
        }),
        ('Amounts', {
            'fields': ('subtotal', 'discounts', 'penalties', 'total_amount', 'amount_paid', 'balance')
        }),
        ('Additional Information', {
            'fields': ('additional_charges', 'notes')
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def is_overdue(self, obj):
        if obj.is_overdue():
            return format_html('<span style="color: red;">Yes</span>')
        return format_html('<span style="color: green;">No</span>')
    is_overdue.short_description = 'Overdue'
    is_overdue.boolean = False

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = [
        'transaction_id', 'student', 'amount', 'payment_date',
        'payment_method', 'payment_status', 'receipt_number'
    ]
    list_filter = ['payment_method', 'payment_status', 'payment_date']
    search_fields = ['transaction_id', 'mpesa_code', 'student__user__first_name']
    date_hierarchy = 'payment_date'
    raw_id_fields = ['student', 'invoice', 'received_by']
    readonly_fields = ['transaction_id', 'receipt_number', 'created_at']
    
    fieldsets = (
        ('Payment Information', {
            'fields': ('transaction_id', 'student', 'invoice', 'amount', 'payment_date')
        }),
        ('Status', {
            'fields': ('payment_method', 'payment_status', 'receipt_number')
        }),
        ('Reference Information', {
            'fields': ('reference_number', 'mpesa_code', 'cheque_number', 'bank_name')
        }),
        ('Additional Information', {
            'fields': ('notes', 'received_by')
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )

@admin.register(ExpenseCategory)
class ExpenseCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'budget_allocation']
    search_fields = ['name', 'code']

@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = [
        'expense_number', 'category', 'description_short', 'amount',
        'expense_date', 'payment_status', 'vendor_name'
    ]
    list_filter = ['category', 'payment_status', 'expense_date']
    search_fields = ['expense_number', 'description', 'vendor_name']
    date_hierarchy = 'expense_date'
    raw_id_fields = ['approved_by', 'created_by']
    readonly_fields = ['expense_number', 'created_at', 'updated_at']
    
    def description_short(self, obj):
        return obj.description[:50] + '...' if len(obj.description) > 50 else obj.description
    description_short.short_description = 'Description'

@admin.register(Budget)
class BudgetAdmin(admin.ModelAdmin):
    list_display = ['academic_year', 'category', 'allocated_amount', 'spent_amount', 'remaining_amount', 'utilization']
    list_filter = ['academic_year', 'category']
    readonly_fields = ['spent_amount', 'remaining_amount']
    
    def utilization(self, obj):
        if obj.allocated_amount > 0:
            percentage = (obj.spent_amount / obj.allocated_amount) * 100
            return format_html('{}%', round(percentage, 1))
        return '0%'
    utilization.short_description = 'Utilization'

@admin.register(FeeReminder)
class FeeReminderAdmin(admin.ModelAdmin):
    list_display = ['student', 'invoice', 'reminder_type', 'scheduled_date', 'status']
    list_filter = ['reminder_type', 'status', 'scheduled_date']
    search_fields = ['student__user__first_name']
    date_hierarchy = 'scheduled_date'

@admin.register(FinancialAid)
class FinancialAidAdmin(admin.ModelAdmin):
    list_display = ['student', 'aid_type', 'amount', 'academic_year', 'provider_name', 'is_active']
    list_filter = ['aid_type', 'academic_year', 'is_active']
    search_fields = ['student__user__first_name', 'provider_name']
    date_hierarchy = 'awarded_date'
    raw_id_fields = ['student', 'created_by']

@admin.register(MpesaTransaction)
class MpesaTransactionAdmin(admin.ModelAdmin):
    list_display = [
        'mpesa_receipt', 'phone_number', 'amount', 'transaction_date',
        'status', 'student_link'
    ]
    list_filter = ['status', 'transaction_type', 'transaction_date']
    search_fields = ['mpesa_receipt', 'phone_number']
    readonly_fields = ['raw_response']
    
    def student_link(self, obj):
        if obj.student:
            url = reverse('admin:students_student_change', args=[obj.student.id])
            return format_html('<a href="{}">{}</a>', url, obj.student.get_full_name())
        return '-'
    student_link.short_description = 'Student'