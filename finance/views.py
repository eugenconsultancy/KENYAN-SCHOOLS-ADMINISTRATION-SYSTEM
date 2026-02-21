from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
import json
from django.db.models import Q, Sum, Count, Avg
from django.core.paginator import Paginator
from django.http import JsonResponse, HttpResponse, FileResponse
from django.utils import timezone
from accounts.decorators import role_required, admin_required
from .models import (
    FeeCategory, FeeStructure, Invoice, Payment, ExpenseCategory,
    Expense, Budget, FeeReminder, FinancialAid, MpesaTransaction
)
from .forms import (
    FeeCategoryForm, FeeStructureForm, InvoiceForm, InvoiceGenerationForm,
    PaymentForm, MpesaPaymentForm, ExpenseCategoryForm, ExpenseForm,
    BudgetForm, FeeReminderForm, FinancialAidForm, DateRangeForm, FeeSearchForm
)
from .services import FinanceService, ReportService, MpesaService
from students.models import Student
from academics.models import AcademicYear
import csv
import json
import os

# ============== Dashboard Views ==============

@login_required
def finance_dashboard(request):
    """Main finance dashboard"""
    
    # Get current academic year
    current_year = AcademicYear.objects.filter(is_current=True).first()
    
    # Summary statistics
    total_invoiced = Invoice.objects.aggregate(total=Sum('total_amount'))['total'] or 0
    total_collected = Payment.objects.filter(
        payment_status='completed'
    ).aggregate(total=Sum('amount'))['total'] or 0
    outstanding = total_invoiced - total_collected
    
    # This month's collections
    month_start = timezone.now().replace(day=1)
    month_collections = Payment.objects.filter(
        payment_status='completed',
        payment_date__gte=month_start
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    # Overdue invoices count
    overdue_invoices = Invoice.objects.filter(
        status='overdue',
        balance__gt=0
    ).count()
    
    # Recent payments
    recent_payments = Payment.objects.filter(
        payment_status='completed'
    ).select_related('student', 'invoice').order_by('-payment_date')[:10]
    
    # Top defaulters
    top_defaulters = Invoice.objects.filter(
        status='overdue',
        balance__gt=0
    ).values('student__user__first_name', 'student__user__last_name').annotate(
        total_balance=Sum('balance')
    ).order_by('-total_balance')[:5]
    
    # Monthly collection chart data
    monthly_data = FinanceService.get_monthly_collection_data()
    
    context = {
        'total_invoiced': total_invoiced,
        'total_collected': total_collected,
        'outstanding': outstanding,
        'month_collections': month_collections,
        'overdue_invoices': overdue_invoices,
        'recent_payments': recent_payments,
        'top_defaulters': top_defaulters,
        'monthly_data': json.dumps(monthly_data),
        'current_year': current_year,
    }
    
    return render(request, 'finance/dashboard.html', context)

# ============== Fee Structure Views ==============

@login_required
@admin_required
def fee_structure_list(request):
    """List all fee structures"""
    fee_structures = FeeStructure.objects.all().select_related('academic_year').order_by(
        '-academic_year', 'term', 'class_level'
    )
    
    # Filters
    academic_year = request.GET.get('academic_year')
    if academic_year:
        fee_structures = fee_structures.filter(academic_year_id=academic_year)
    
    term = request.GET.get('term')
    if term:
        fee_structures = fee_structures.filter(term=term)
    
    class_level = request.GET.get('class_level')
    if class_level:
        fee_structures = fee_structures.filter(class_level=class_level)
    
    context = {
        'fee_structures': fee_structures,
        'academic_years': AcademicYear.objects.all(),
    }
    
    return render(request, 'finance/fee_structure_list.html', context)

@login_required
@admin_required
def fee_structure_create(request):
    """Create new fee structure"""
    if request.method == 'POST':
        form = FeeStructureForm(request.POST)
        if form.is_valid():
            fee_structure = form.save(commit=False)
            fee_structure.created_by = request.user
            fee_structure.save()
            messages.success(request, 'Fee structure created successfully.')
            return redirect('finance:fee_structure_list')
    else:
        form = FeeStructureForm()
    
    return render(request, 'finance/fee_structure_form.html', {
        'form': form,
        'title': 'Create Fee Structure'
    })

@login_required
@admin_required
def fee_structure_edit(request, pk):
    """Edit fee structure"""
    fee_structure = get_object_or_404(FeeStructure, pk=pk)
    
    if request.method == 'POST':
        form = FeeStructureForm(request.POST, instance=fee_structure)
        if form.is_valid():
            form.save()
            messages.success(request, 'Fee structure updated successfully.')
            return redirect('finance:fee_structure_list')
    else:
        form = FeeStructureForm(instance=fee_structure)
    
    return render(request, 'finance/fee_structure_form.html', {
        'form': form,
        'fee_structure': fee_structure,
        'title': 'Edit Fee Structure'
    })

@login_required
@admin_required
def fee_structure_delete(request, pk):
    """Delete fee structure"""
    fee_structure = get_object_or_404(FeeStructure, pk=pk)
    
    if request.method == 'POST':
        fee_structure.delete()
        messages.success(request, 'Fee structure deleted successfully.')
        return redirect('finance:fee_structure_list')
    
    return render(request, 'finance/fee_structure_confirm_delete.html', {
        'fee_structure': fee_structure
    })

# ============== Invoice Views ==============

@login_required
def invoice_list(request):
    """List all invoices"""
    invoices = Invoice.objects.all().select_related(
        'student', 'fee_structure'
    ).order_by('-issue_date')
    
    # Apply filters
    form = FeeSearchForm(request.GET)
    if form.is_valid():
        if form.cleaned_data.get('query'):
            query = form.cleaned_data['query']
            invoices = invoices.filter(
                Q(student__user__first_name__icontains=query) |
                Q(student__user__last_name__icontains=query) |
                Q(student__admission_number__icontains=query) |
                Q(invoice_number__icontains=query)
            )
        if form.cleaned_data.get('academic_year'):
            invoices = invoices.filter(fee_structure__academic_year=form.cleaned_data['academic_year'])
        if form.cleaned_data.get('term'):
            invoices = invoices.filter(fee_structure__term=form.cleaned_data['term'])
        if form.cleaned_data.get('class_level'):
            invoices = invoices.filter(student__current_class=form.cleaned_data['class_level'])
        if form.cleaned_data.get('status'):
            invoices = invoices.filter(status=form.cleaned_data['status'])
    
    paginator = Paginator(invoices, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'form': form,
    }
    
    return render(request, 'finance/invoice_list.html', context)

@login_required
def invoice_detail(request, pk):
    """View invoice details"""
    invoice = get_object_or_404(Invoice, pk=pk)
    payments = invoice.payments.filter(payment_status='completed').order_by('-payment_date')
    
    context = {
        'invoice': invoice,
        'payments': payments,
        'breakdown': invoice.fee_structure.get_breakdown() if invoice.fee_structure else {},
    }
    
    return render(request, 'finance/invoice_detail.html', context)

@login_required
@admin_required
def invoice_create(request):
    """Create new invoice"""
    if request.method == 'POST':
        form = InvoiceForm(request.POST)
        if form.is_valid():
            invoice = form.save(commit=False)
            
            # Calculate amounts
            fee_structure = invoice.fee_structure
            invoice.subtotal = fee_structure.get_total_fee()
            
            # Calculate total with discounts and penalties
            invoice.total_amount = invoice.subtotal - invoice.discounts + invoice.penalties
            
            # Process additional charges if any
            if form.cleaned_data.get('additional_charges'):
                invoice.additional_charges = json.loads(form.cleaned_data['additional_charges'])
                for charge in invoice.additional_charges:
                    invoice.total_amount += charge['amount']
            
            invoice.created_by = request.user
            invoice.save()
            
            messages.success(request, f'Invoice {invoice.invoice_number} created successfully.')
            return redirect('finance:invoice_detail', pk=invoice.pk)
    else:
        form = InvoiceForm()
    
    return render(request, 'finance/invoice_form.html', {
        'form': form,
        'title': 'Create Invoice'
    })

@login_required
@admin_required
def invoice_generate_bulk(request):
    """Bulk generate invoices"""
    if request.method == 'POST':
        form = InvoiceGenerationForm(request.POST)
        if form.is_valid():
            results = form.generate_invoices(request.user)
            
            messages.success(
                request,
                f'Generated {results["generated"]} invoices. '
                f'{results["skipped"]} skipped (already exist).'
            )
            return redirect('finance:invoice_list')
    else:
        form = InvoiceGenerationForm()
    
    return render(request, 'finance/invoice_generate_bulk.html', {'form': form})

@login_required
def student_invoices(request, student_id):
    """View invoices for a specific student"""
    student = get_object_or_404(Student, id=student_id)
    
    # Check permission
    if not (request.user.is_admin() or request.user == student.user):
        messages.error(request, 'You do not have permission to view this page.')
        return redirect('dashboard:home')
    
    invoices = Invoice.objects.filter(student=student).order_by('-issue_date')
    
    # Get summary
    total_invoiced = invoices.aggregate(total=Sum('total_amount'))['total'] or 0
    total_paid = Payment.objects.filter(
        student=student,
        payment_status='completed'
    ).aggregate(total=Sum('amount'))['total'] or 0
    balance = total_invoiced - total_paid
    
    context = {
        'student': student,
        'invoices': invoices,
        'total_invoiced': total_invoiced,
        'total_paid': total_paid,
        'balance': balance,
    }
    
    return render(request, 'finance/student_invoices.html', context)

# ============== Payment Views ==============

@login_required
def payment_list(request):
    """List all payments"""
    payments = Payment.objects.filter(
        payment_status='completed'
    ).select_related('student', 'invoice').order_by('-payment_date')
    
    # Date filter
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    if start_date:
        payments = payments.filter(payment_date__date__gte=start_date)
    if end_date:
        payments = payments.filter(payment_date__date__lte=end_date)
    
    paginator = Paginator(payments, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'start_date': start_date,
        'end_date': end_date,
    }
    
    return render(request, 'finance/payment_list.html', context)

@login_required
def payment_detail(request, pk):
    """View payment details"""
    payment = get_object_or_404(Payment, pk=pk)
    
    return render(request, 'finance/payment_detail.html', {'payment': payment})

@login_required
@admin_required
def payment_create(request):
    """Record new payment"""
    if request.method == 'POST':
        form = PaymentForm(request.POST)
        if form.is_valid():
            payment = form.save(commit=False)
            payment.received_by = request.user
            payment.payment_status = 'completed'
            payment.save()
            
            messages.success(request, f'Payment of {payment.amount} recorded successfully.')
            return redirect('finance:payment_detail', pk=payment.pk)
    else:
        form = PaymentForm()
    
    return render(request, 'finance/payment_form.html', {
        'form': form,
        'title': 'Record Payment'
    })

@login_required
def mpesa_payment(request):
    """Initiate M-Pesa payment"""
    if request.method == 'POST':
        form = MpesaPaymentForm(request.POST)
        if form.is_valid():
            # Initiate STK Push
            response = MpesaService.initiate_stk_push(
                phone_number=form.cleaned_data['phone_number'],
                amount=form.cleaned_data['amount'],
                student=form.cleaned_data['student'],
                invoice=form.cleaned_data.get('invoice')
            )
            
            if response.get('success'):
                messages.success(request, 'M-Pesa STK push sent. Please check your phone.')
                return redirect('finance:payment_list')
            else:
                messages.error(request, f'M-Pesa payment failed: {response.get("error")}')
    else:
        form = MpesaPaymentForm()
    
    return render(request, 'finance/mpesa_payment.html', {'form': form})

@login_required
def mpesa_callback(request):
    """M-Pesa callback URL"""
    if request.method == 'POST':
        data = json.loads(request.body)
        MpesaService.process_callback(data)
        return JsonResponse({'ResultCode': 0, 'ResultDesc': 'Success'})
    
    return JsonResponse({'error': 'Invalid method'}, status=400)

# ============== Expense Views ==============

@login_required
@admin_required
def expense_list(request):
    """List all expenses"""
    expenses = Expense.objects.all().select_related(
        'category', 'created_by'
    ).order_by('-expense_date')
    
    # Filter by category
    category = request.GET.get('category')
    if category:
        expenses = expenses.filter(category_id=category)
    
    # Date range filter
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    if start_date:
        expenses = expenses.filter(expense_date__gte=start_date)
    if end_date:
        expenses = expenses.filter(expense_date__lte=end_date)
    
    paginator = Paginator(expenses, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Summary
    total_expenses = expenses.aggregate(total=Sum('amount'))['total'] or 0
    
    context = {
        'page_obj': page_obj,
        'total_expenses': total_expenses,
        'categories': ExpenseCategory.objects.all(),
    }
    
    return render(request, 'finance/expense_list.html', context)

@login_required
@admin_required
def expense_create(request):
    """Create new expense"""
    if request.method == 'POST':
        form = ExpenseForm(request.POST, request.FILES)
        if form.is_valid():
            expense = form.save(commit=False)
            expense.created_by = request.user
            expense.save()
            
            messages.success(request, 'Expense recorded successfully.')
            return redirect('finance:expense_list')
    else:
        form = ExpenseForm()
    
    return render(request, 'finance/expense_form.html', {
        'form': form,
        'title': 'Record Expense'
    })

@login_required
@admin_required
def expense_detail(request, pk):
    """View expense details"""
    expense = get_object_or_404(Expense, pk=pk)
    
    return render(request, 'finance/expense_detail.html', {'expense': expense})

@login_required
@admin_required
def expense_approve(request, pk):
    """Approve expense"""
    expense = get_object_or_404(Expense, pk=pk)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'approve':
            expense.payment_status = 'approved'
            expense.approved_by = request.user
            expense.approved_at = timezone.now()
            messages.success(request, 'Expense approved.')
        elif action == 'reject':
            expense.payment_status = 'rejected'
            expense.approved_by = request.user
            expense.approved_at = timezone.now()
            messages.success(request, 'Expense rejected.')
        
        expense.save()
        
        return redirect('finance:expense_detail', pk=expense.pk)
    
    return render(request, 'finance/expense_approve.html', {'expense': expense})

# ============== Budget Views ==============

@login_required
@admin_required
def budget_list(request):
    """List budgets"""
    budgets = Budget.objects.all().select_related(
        'academic_year', 'category'
    ).order_by('-academic_year', 'category')
    
    # Update spent amounts
    for budget in budgets:
        budget.update_spent_amount()
    
    context = {
        'budgets': budgets,
    }
    
    return render(request, 'finance/budget_list.html', context)

@login_required
@admin_required
def budget_create(request):
    """Create budget"""
    if request.method == 'POST':
        form = BudgetForm(request.POST)
        if form.is_valid():
            budget = form.save()
            messages.success(request, 'Budget created successfully.')
            return redirect('finance:budget_list')
    else:
        form = BudgetForm()
    
    return render(request, 'finance/budget_form.html', {
        'form': form,
        'title': 'Create Budget'
    })

@login_required
@admin_required
def budget_edit(request, pk):
    """Edit budget"""
    budget = get_object_or_404(Budget, pk=pk)
    
    if request.method == 'POST':
        form = BudgetForm(request.POST, instance=budget)
        if form.is_valid():
            form.save()
            messages.success(request, 'Budget updated successfully.')
            return redirect('finance:budget_list')
    else:
        form = BudgetForm(instance=budget)
    
    return render(request, 'finance/budget_form.html', {
        'form': form,
        'budget': budget,
        'title': 'Edit Budget'
    })

# ============== Financial Aid Views ==============

@login_required
@admin_required
def financial_aid_list(request):
    """List financial aid records"""
    aids = FinancialAid.objects.all().select_related(
        'student', 'academic_year'
    ).order_by('-awarded_date')
    
    paginator = Paginator(aids, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
    }
    
    return render(request, 'finance/financial_aid_list.html', context)

@login_required
@admin_required
def financial_aid_create(request):
    """Create financial aid record"""
    if request.method == 'POST':
        form = FinancialAidForm(request.POST)
        if form.is_valid():
            aid = form.save(commit=False)
            aid.created_by = request.user
            aid.save()
            
            messages.success(request, 'Financial aid record created successfully.')
            return redirect('finance:financial_aid_list')
    else:
        form = FinancialAidForm()
    
    return render(request, 'finance/financial_aid_form.html', {
        'form': form,
        'title': 'Add Financial Aid'
    })

@login_required
@admin_required
def financial_aid_edit(request, pk):
    """Edit financial aid record"""
    aid = get_object_or_404(FinancialAid, pk=pk)
    
    if request.method == 'POST':
        form = FinancialAidForm(request.POST, instance=aid)
        if form.is_valid():
            form.save()
            messages.success(request, 'Financial aid record updated successfully.')
            return redirect('finance:financial_aid_list')
    else:
        form = FinancialAidForm(instance=aid)
    
    return render(request, 'finance/financial_aid_form.html', {
        'form': form,
        'aid': aid,
        'title': 'Edit Financial Aid'
    })

# ============== Report Views ==============

@login_required
def reports(request):
    """Reports dashboard"""
    return render(request, 'finance/reports.html')

@login_required
def collection_report(request):
    """Generate collection report"""
    form = DateRangeForm(request.GET or None)
    
    if form.is_valid():
        data = ReportService.get_collection_report(
            form.cleaned_data['start_date'],
            form.cleaned_data['end_date']
        )
    else:
        # Default to current month
        today = timezone.now().date()
        start_date = today.replace(day=1)
        end_date = today
        data = ReportService.get_collection_report(start_date, end_date)
    
    return render(request, 'finance/collection_report.html', {
        'form': form,
        'data': data,
    })

@login_required
def outstanding_report(request):
    """Generate outstanding fees report"""
    data = ReportService.get_outstanding_report()
    
    return render(request, 'finance/outstanding_report.html', {'data': data})

@login_required
def expense_report(request):
    """Generate expense report"""
    form = DateRangeForm(request.GET or None)
    
    if form.is_valid():
        data = ReportService.get_expense_report(
            form.cleaned_data['start_date'],
            form.cleaned_data['end_date']
        )
    else:
        # Default to current month
        today = timezone.now().date()
        start_date = today.replace(day=1)
        end_date = today
        data = ReportService.get_expense_report(start_date, end_date)
    
    return render(request, 'finance/expense_report.html', {
        'form': form,
        'data': data,
    })

@login_required
def student_statement(request, student_id):
    """Generate fee statement for a student"""
    student = get_object_or_404(Student, id=student_id)
    
    # Check permission
    if not (request.user.is_admin() or request.user == student.user):
        messages.error(request, 'You do not have permission to view this page.')
        return redirect('dashboard:home')
    
    data = ReportService.get_student_statement(student)
    
    return render(request, 'finance/student_statement.html', {
        'student': student,
        'data': data,
    })

# ============== Export Views ==============

@login_required
def export_payments(request):
    """Export payments to CSV"""
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    payments = Payment.objects.filter(payment_status='completed')
    
    if start_date:
        payments = payments.filter(payment_date__date__gte=start_date)
    if end_date:
        payments = payments.filter(payment_date__date__lte=end_date)
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="payments_{start_date}_to_{end_date}.csv"'
    
    writer = csv.writer(response)
    writer.writerow([
        'Date', 'Transaction ID', 'Student Name', 'Admission No',
        'Amount', 'Method', 'Reference', 'Invoice No'
    ])
    
    for payment in payments:
        writer.writerow([
            payment.payment_date.strftime('%Y-%m-%d %H:%M'),
            payment.transaction_id,
            payment.student.get_full_name(),
            payment.student.admission_number,
            payment.amount,
            payment.get_payment_method_display(),
            payment.reference_number or payment.mpesa_code or payment.cheque_number,
            payment.invoice.invoice_number if payment.invoice else 'N/A'
        ])
    
    return response

@login_required
def export_invoices(request):
    """Export invoices to CSV"""
    invoices = Invoice.objects.all().select_related('student', 'fee_structure')
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="invoices.csv"'
    
    writer = csv.writer(response)
    writer.writerow([
        'Invoice No', 'Date', 'Student Name', 'Admission No',
        'Class', 'Total Amount', 'Paid', 'Balance', 'Status', 'Due Date'
    ])
    
    for invoice in invoices:
        writer.writerow([
            invoice.invoice_number,
            invoice.issue_date.strftime('%Y-%m-%d'),
            invoice.student.get_full_name(),
            invoice.student.admission_number,
            f"Form {invoice.student.current_class} {invoice.student.stream}",
            invoice.total_amount,
            invoice.amount_paid,
            invoice.balance,
            invoice.get_status_display(),
            invoice.due_date.strftime('%Y-%m-%d'),
        ])
    
    return response


@login_required
@admin_required
def export_budgets(request):
    """Export budgets to CSV"""
    import csv
    from django.http import HttpResponse
    
    # Get filters
    year = request.GET.get('year')
    status = request.GET.get('status')
    
    budgets = Budget.objects.all().select_related('academic_year', 'category')
    
    if year:
        budgets = budgets.filter(academic_year__name=year)
    
    # Create CSV response
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="budgets.csv"'
    
    writer = csv.writer(response)
    writer.writerow([
        'Academic Year', 'Category', 'Allocated Amount', 'Spent Amount',
        'Remaining Amount', 'Utilization %', 'Status'
    ])
    
    for budget in budgets:
        utilization = (budget.spent_amount / budget.allocated_amount * 100) if budget.allocated_amount > 0 else 0
        
        if utilization > 100:
            status_text = 'Over Budget'
        elif utilization > 80:
            status_text = 'Warning'
        else:
            status_text = 'On Track'
        
        writer.writerow([
            budget.academic_year.name,
            budget.category.name,
            budget.allocated_amount,
            budget.spent_amount,
            budget.remaining_amount,
            f"{utilization:.1f}%",
            status_text
        ])
    
    return response

# ============== API Views ==============

@login_required
def get_student_balance(request, student_id):
    """API endpoint to get student balance"""
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        balance = FinanceService.get_student_balance(student_id)
        return JsonResponse({'balance': float(balance)})
    
    return JsonResponse({'error': 'Invalid request'}, status=400)

@login_required
def get_invoice_details(request, invoice_id):
    """API endpoint to get invoice details"""
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        invoice = get_object_or_404(Invoice, id=invoice_id)
        data = {
            'id': invoice.id,
            'number': invoice.invoice_number,
            'total': float(invoice.total_amount),
            'paid': float(invoice.amount_paid),
            'balance': float(invoice.balance),
            'status': invoice.get_status_display(),
        }
        return JsonResponse(data)
    
    return JsonResponse({'error': 'Invalid request'}, status=400)
@login_required
def budget_report(request, year):
    """Generate budget report for a specific year"""
    from .services import ReportService
    pdf_path = ReportService.generate_budget_report(year)
    
    if pdf_path and os.path.exists(pdf_path):
        filename = f"budget_report_{year}.pdf"
        return FileResponse(open(pdf_path, "rb"), content_type="application/pdf", filename=filename)
    else:
        messages.error(request, "Error generating budget report.")
        return redirect("finance:budget_list")
