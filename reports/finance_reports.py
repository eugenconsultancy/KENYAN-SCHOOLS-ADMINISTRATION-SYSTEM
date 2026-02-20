"""
Finance Reports Module
Handles generation of financial reports
"""

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from django.utils import timezone
from django.db.models import Sum, Count, Q
from .report_generator import ReportGenerator
from finance.models import Invoice, Payment, Expense, Budget, FinancialAid
from students.models import Student
import datetime

class FinanceReportGenerator(ReportGenerator):
    """Generator for financial reports"""
    
    @staticmethod
    def generate_fee_statement(student):
        """Generate fee statement for a student"""
        
        generator = ReportGenerator(f"Fee Statement: {student.get_fullName()}")
        generator.add_header_info(
            Admission=student.admission_number,
            Class=student.get_current_class_name()
        )
        
        # Get all invoices for this student
        invoices = Invoice.objects.filter(student=student).order_by('issue_date')
        
        if not invoices.exists():
            generator.add_paragraph("No fee records found for this student.")
            return generator.generate()
        
        # Summary
        generator.add_subtitle("Financial Summary")
        
        total_invoiced = invoices.aggregate(total=Sum('total_amount'))['total'] or 0
        total_paid = Payment.objects.filter(
            student=student,
            payment_status='completed'
        ).aggregate(total=Sum('amount'))['total'] or 0
        outstanding = total_invoiced - total_paid
        
        summary_data = [
            ['Total Fees Invoiced', f"KSh {total_invoiced:,.2f}"],
            ['Total Amount Paid', f"KSh {total_paid:,.2f}"],
            ['Outstanding Balance', f"KSh {outstanding:,.2f}"],
            ['Payment Status', 'Fully Paid' if outstanding <= 0 else 'Partial Payment'],
        ]
        
        generator.add_table(summary_data, col_widths=[3*inch, 3*inch])
        
        # Invoice Details
        generator.add_subtitle("Invoice History")
        
        invoice_data = [['Invoice No.', 'Date', 'Description', 'Amount', 'Paid', 'Balance', 'Status']]
        for invoice in invoices:
            invoice_data.append([
                invoice.invoice_number,
                invoice.issue_date.strftime('%Y-%m-%d'),
                str(invoice.fee_structure) if invoice.fee_structure else 'N/A',
                f"KSh {invoice.total_amount:,.2f}",
                f"KSh {invoice.amount_paid:,.2f}",
                f"KSh {invoice.balance:,.2f}",
                invoice.get_status_display()
            ])
        
        generator.add_table(invoice_data, col_widths=[1*inch, 0.8*inch, 1.5*inch, 0.9*inch, 0.9*inch, 0.9*inch, 0.8*inch])
        
        # Payment History
        payments = Payment.objects.filter(
            student=student,
            payment_status='completed'
        ).order_by('-payment_date')
        
        if payments.exists():
            generator.add_subtitle("Payment History")
            
            payment_data = [['Date', 'Transaction ID', 'Method', 'Amount', 'Receipt No.']]
            for payment in payments:
                payment_data.append([
                    payment.payment_date.strftime('%Y-%m-%d %H:%M'),
                    payment.transaction_id,
                    payment.get_payment_method_display(),
                    f"KSh {payment.amount:,.2f}",
                    payment.receipt_number or '-'
                ])
            
            generator.add_table(payment_data, col_widths=[1.2*inch, 1.5*inch, 1*inch, 1*inch, 1.2*inch])
        
        # Outstanding Invoices Detail
        outstanding_invoices = invoices.filter(balance__gt=0)
        if outstanding_invoices.exists():
            generator.add_page_break()
            generator.add_subtitle("Outstanding Invoices Detail")
            
            outstanding_data = [['Invoice No.', 'Due Date', 'Total', 'Outstanding', 'Days Overdue']]
            today = timezone.now().date()
            
            for invoice in outstanding_invoices:
                if invoice.due_date < today:
                    days_overdue = (today - invoice.due_date).days
                else:
                    days_overdue = 0
                
                outstanding_data.append([
                    invoice.invoice_number,
                    invoice.due_date.strftime('%Y-%m-%d'),
                    f"KSh {invoice.total_amount:,.2f}",
                    f"KSh {invoice.balance:,.2f}",
                    str(days_overdue)
                ])
            
            generator.add_table(outstanding_data, col_widths=[1*inch, 1*inch, 1.2*inch, 1.2*inch, 1*inch])
        
        generator.add_signature_block()
        
        return generator.generate()
    
    @staticmethod
    def generate_collection_report(start_date, end_date):
        """Generate fee collection report for date range"""
        
        generator = ReportGenerator(f"Fee Collection Report")
        generator.add_header_info(Period=f"{start_date} to {end_date}")
        
        # Get payments in date range
        payments = Payment.objects.filter(
            payment_status='completed',
            payment_date__date__gte=start_date,
            payment_date__date__lte=end_date
        ).select_related('student')
        
        if not payments.exists():
            generator.add_paragraph("No payments found in this period.")
            return generator.generate()
        
        # Summary Statistics
        generator.add_subtitle("Collection Summary")
        
        total_collected = payments.aggregate(total=Sum('amount'))['total'] or 0
        total_transactions = payments.count()
        avg_transaction = total_collected / total_transactions if total_transactions > 0 else 0
        
        # Payment method breakdown
        cash_total = payments.filter(payment_method='cash').aggregate(total=Sum('amount'))['total'] or 0
        mpesa_total = payments.filter(payment_method='mpesa').aggregate(total=Sum('amount'))['total'] or 0
        bank_total = payments.filter(payment_method='bank_transfer').aggregate(total=Sum('amount'))['total'] or 0
        cheque_total = payments.filter(payment_method='cheque').aggregate(total=Sum('amount'))['total'] or 0
        
        summary_data = [
            ['Total Collected', f"KSh {total_collected:,.2f}"],
            ['Number of Transactions', str(total_transactions)],
            ['Average Transaction', f"KSh {avg_transaction:,.2f}"],
            ['Cash Payments', f"KSh {cash_total:,.2f}"],
            ['M-Pesa Payments', f"KSh {mpesa_total:,.2f}"],
            ['Bank Transfers', f"KSh {bank_total:,.2f}"],
            ['Cheque Payments', f"KSh {cheque_total:,.2f}"],
        ]
        
        generator.add_table(summary_data, col_widths=[3*inch, 3*inch])
        
        # Daily Breakdown
        generator.add_subtitle("Daily Collections")
        
        # Group by date
        dates = payments.dates('payment_date', 'day').order_by('payment_date')
        daily_data = [['Date', 'Transactions', 'Amount']]
        
        for date in dates:
            day_payments = payments.filter(payment_date__date=date)
            day_count = day_payments.count()
            day_amount = day_payments.aggregate(total=Sum('amount'))['total'] or 0
            
            daily_data.append([
                date.strftime('%Y-%m-%d'),
                str(day_count),
                f"KSh {day_amount:,.2f}"
            ])
        
        generator.add_table(daily_data, col_widths=[2*inch, 2*inch, 2*inch])
        
        # Class-wise Collection
        generator.add_page_break()
        generator.add_subtitle("Class-wise Collections")
        
        class_data = [['Class', 'Students', 'Amount Collected', 'Average per Student']]
        
        for level in range(1, 5):
            class_students = Student.objects.filter(current_class=level, is_active=True)
            student_ids = class_students.values_list('id', flat=True)
            
            class_payments = payments.filter(student_id__in=student_ids)
            if class_payments.exists():
                class_total = class_payments.aggregate(total=Sum('amount'))['total'] or 0
                student_count = class_students.count()
                avg_per_student = class_total / student_count if student_count > 0 else 0
                
                class_data.append([
                    f"Form {level}",
                    str(student_count),
                    f"KSh {class_total:,.2f}",
                    f"KSh {avg_per_student:,.2f}"
                ])
        
        generator.add_table(class_data, col_widths=[1.5*inch, 1.5*inch, 2*inch, 2*inch])
        
        # Detailed Transaction List
        generator.add_page_break()
        generator.add_subtitle("Detailed Transaction List")
        
        transaction_data = [['Date', 'Student', 'Admission No.', 'Method', 'Amount', 'Receipt No.']]
        for payment in payments.order_by('-payment_date')[:100]:  # Limit to last 100
            transaction_data.append([
                payment.payment_date.strftime('%Y-%m-%d %H:%M'),
                payment.student.get_full_name(),
                payment.student.admission_number,
                payment.get_payment_method_display(),
                f"KSh {payment.amount:,.2f}",
                payment.receipt_number or '-'
            ])
        
        generator.add_table(transaction_data, col_widths=[1.2*inch, 1.5*inch, 1*inch, 1*inch, 1*inch, 1*inch])
        
        generator.add_signature_block()
        
        return generator.generate()
    
    @staticmethod
    def generate_outstanding_report(as_at_date):
        """Generate outstanding fees report"""
        
        generator = ReportGenerator(f"Outstanding Fees Report")
        generator.add_header_info(AsAt=as_at_date)
        
        # Get all invoices with outstanding balance
        invoices = Invoice.objects.filter(
            balance__gt=0,
            status__in=['sent', 'partially_paid', 'overdue']
        ).select_related('student', 'fee_structure')
        
        if not invoices.exists():
            generator.add_paragraph("No outstanding fees as at this date.")
            return generator.generate()
        
        # Summary
        generator.add_subtitle("Summary")
        
        total_outstanding = invoices.aggregate(total=Sum('balance'))['total'] or 0
        total_invoices = invoices.count()
        avg_outstanding = total_outstanding / total_invoices if total_invoices > 0 else 0
        
        # Overdue summary
        today = timezone.now().date()
        overdue_invoices = invoices.filter(due_date__lt=today)
        total_overdue = overdue_invoices.aggregate(total=Sum('balance'))['total'] or 0
        overdue_count = overdue_invoices.count()
        
        summary_data = [
            ['Total Outstanding', f"KSh {total_outstanding:,.2f}"],
            ['Number of Invoices', str(total_invoices)],
            ['Average Outstanding', f"KSh {avg_outstanding:,.2f}"],
            ['Overdue Invoices', str(overdue_count)],
            ['Overdue Amount', f"KSh {total_overdue:,.2f}"],
        ]
        
        generator.add_table(summary_data, col_widths=[3*inch, 3*inch])
        
        # Class-wise Outstanding
        generator.add_subtitle("Outstanding by Class")
        
        class_data = [['Class', 'Students with Arrears', 'Total Outstanding', 'Average']]
        
        for level in range(1, 5):
            class_invoices = invoices.filter(student__current_class=level)
            if class_invoices.exists():
                class_total = class_invoices.aggregate(total=Sum('balance'))['total'] or 0
                student_count = class_invoices.values('student').distinct().count()
                class_avg = class_total / student_count if student_count > 0 else 0
                
                class_data.append([
                    f"Form {level}",
                    str(student_count),
                    f"KSh {class_total:,.2f}",
                    f"KSh {class_avg:,.2f}"
                ])
        
        generator.add_table(class_data, col_widths=[1.5*inch, 1.5*inch, 2*inch, 2*inch])
        
        # Detailed Outstanding List
        generator.add_page_break()
        generator.add_subtitle("Detailed Outstanding List")
        
        # Sort by amount (highest first)
        invoices = invoices.order_by('-balance')
        
        detail_data = [['#', 'Student Name', 'Admission No.', 'Class', 'Invoice No.', 'Due Date', 'Outstanding', 'Status']]
        for i, invoice in enumerate(invoices, 1):
            status = invoice.get_status_display()
            if invoice.due_date < today:
                status = f"{status} (Overdue)"
            
            detail_data.append([
                str(i),
                invoice.student.get_full_name(),
                invoice.student.admission_number,
                invoice.student.get_current_class_name(),
                invoice.invoice_number,
                invoice.due_date.strftime('%Y-%m-%d'),
                f"KSh {invoice.balance:,.2f}",
                status
            ])
        
        generator.add_table(detail_data, col_widths=[0.4*inch, 1.5*inch, 1*inch, 0.8*inch, 1*inch, 0.8*inch, 1.2*inch, 1*inch])
        
        generator.add_signature_block()
        
        return generator.generate()
    
    @staticmethod
    def generate_budget_report(year):
        """Generate budget vs actual report"""
        
        generator = ReportGenerator(f"Budget Report - {year}")
        generator.add_header_info()
        
        # Get all budgets for the year
        from academics.models import AcademicYear
        academic_year = AcademicYear.objects.filter(name=str(year)).first()
        
        if not academic_year:
            generator.add_paragraph(f"No budget data found for year {year}.")
            return generator.generate()
        
        budgets = Budget.objects.filter(academic_year=academic_year).select_related('category')
        
        if not budgets.exists():
            generator.add_paragraph(f"No budget data found for year {year}.")
            return generator.generate()
        
        # Overall Summary
        generator.add_subtitle("Budget Overview")
        
        total_allocated = budgets.aggregate(total=Sum('allocated_amount'))['total'] or 0
        total_spent = budgets.aggregate(total=Sum('spent_amount'))['total'] or 0
        total_remaining = total_allocated - total_spent
        utilization = (total_spent / total_allocated * 100) if total_allocated > 0 else 0
        
        summary_data = [
            ['Total Budget Allocated', f"KSh {total_allocated:,.2f}"],
            ['Total Expenditure', f"KSh {total_spent:,.2f}"],
            ['Remaining Balance', f"KSh {total_remaining:,.2f}"],
            ['Utilization Rate', f"{utilization:.1f}%"],
        ]
        
        generator.add_table(summary_data, col_widths=[3*inch, 3*inch])
        
        # Category-wise Breakdown
        generator.add_subtitle("Budget by Category")
        
        category_data = [['Category', 'Allocated', 'Spent', 'Remaining', 'Utilization']]
        
        for budget in budgets:
            utilization = (budget.spent_amount / budget.allocated_amount * 100) if budget.allocated_amount > 0 else 0
            status = "Under Budget" if budget.remaining_amount >= 0 else "Over Budget"
            
            category_data.append([
                budget.category.name,
                f"KSh {budget.allocated_amount:,.2f}",
                f"KSh {budget.spent_amount:,.2f}",
                f"KSh {budget.remaining_amount:,.2f}",
                f"{utilization:.1f}% ({status})"
            ])
        
        generator.add_table(category_data, colWidths=[1.5*inch, 1.2*inch, 1.2*inch, 1.2*inch, 1.5*inch])
        
        # Expense Details
        generator.add_page_break()
        generator.add_subtitle("Detailed Expenditure")
        
        expenses = Expense.objects.filter(
            expense_date__year=year,
            payment_status='paid'
        ).select_related('category').order_by('-expense_date')
        
        if expenses.exists():
            expense_data = [['Date', 'Category', 'Description', 'Vendor', 'Amount']]
            
            for expense in expenses:
                expense_data.append([
                    expense.expense_date.strftime('%Y-%m-%d'),
                    expense.category.name,
                    expense.description[:40] + ('...' if len(expense.description) > 40 else ''),
                    expense.vendor_name,
                    f"KSh {expense.amount:,.2f}"
                ])
            
            generator.add_table(expense_data, col_widths=[0.8*inch, 1*inch, 2*inch, 1.2*inch, 1*inch])
        else:
            generator.add_paragraph("No expenses recorded for this year.")
        
        generator.add_signature_block()
        
        return generator.generate()