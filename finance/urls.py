from django.urls import path
from . import views

app_name = 'finance'

urlpatterns = [
    # Dashboard
    path('', views.finance_dashboard, name='dashboard'),
    
    # Fee Structure
    path('fee-structures/', views.fee_structure_list, name='fee_structure_list'),
    path('fee-structures/create/', views.fee_structure_create, name='fee_structure_create'),
    path('fee-structures/<int:pk>/edit/', views.fee_structure_edit, name='fee_structure_edit'),
    path('fee-structures/<int:pk>/delete/', views.fee_structure_delete, name='fee_structure_delete'),
    
    # Invoices
    path('invoices/', views.invoice_list, name='invoice_list'),
    path('invoices/create/', views.invoice_create, name='invoice_create'),
    path('invoices/generate-bulk/', views.invoice_generate_bulk, name='invoice_generate_bulk'),
    path('invoices/<int:pk>/', views.invoice_detail, name='invoice_detail'),
    path('students/<int:student_id>/invoices/', views.student_invoices, name='student_invoices'),
    
    # Payments
    path('payments/', views.payment_list, name='payment_list'),
    path('payments/create/', views.payment_create, name='payment_create'),
    path('payments/<int:pk>/', views.payment_detail, name='payment_detail'),
    path('payments/mpesa/', views.mpesa_payment, name='mpesa_payment'),
    path('payments/mpesa/callback/', views.mpesa_callback, name='mpesa_callback'),
    
    # Expenses
    path('expenses/', views.expense_list, name='expense_list'),
    path('expenses/create/', views.expense_create, name='expense_create'),
    path('expenses/<int:pk>/', views.expense_detail, name='expense_detail'),
    path('expenses/<int:pk>/approve/', views.expense_approve, name='expense_approve'),
    
    # Budgets
    path('budgets/', views.budget_list, name='budget_list'),
    path('budgets/create/', views.budget_create, name='budget_create'),
    path('budgets/<int:pk>/edit/', views.budget_edit, name='budget_edit'),
    
    # Financial Aid
    path('financial-aid/', views.financial_aid_list, name='financial_aid_list'),
    path('financial-aid/create/', views.financial_aid_create, name='financial_aid_create'),
    path('financial-aid/<int:pk>/edit/', views.financial_aid_edit, name='financial_aid_edit'),
    
    # Reports
    path('reports/', views.reports, name='reports'),
    path('reports/collections/', views.collection_report, name='collection_report'),
    path('reports/outstanding/', views.outstanding_report, name='outstanding_report'),
    path('reports/expenses/', views.expense_report, name='expense_report'),
    path('reports/statement/<int:student_id>/', views.student_statement, name='student_statement'),
    
    # Exports
    path('export/payments/', views.export_payments, name='export_payments'),
    path('export/invoices/', views.export_invoices, name='export_invoices'),
    
    # API endpoints
    path('api/student-balance/<int:student_id>/', views.get_student_balance, name='api_student_balance'),
    path('api/invoice-details/<int:invoice_id>/', views.get_invoice_details, name='api_invoice_details'),
]
