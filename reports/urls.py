from django.urls import path
from . import views

app_name = 'reports'

urlpatterns = [
    # Dashboard
    path('', views.report_index, name='index'),
    
    # Student Reports
    path('student/<int:student_id>/', views.student_report, name='student_report'),
    path('student-list/', views.student_list_report, name='student_list_report'),
    
    # Academic Reports
    path('class/<int:class_id>/exam/<int:exam_id>/result-slips/', views.class_result_slip, name='class_result_slip'),
    path('term/<int:term_id>/', views.term_report, name='term_report'),
    path('exam/<int:exam_id>/performance/', views.exam_performance_report, name='exam_performance_report'),
    path('rankings/<int:term_id>/', views.ranking_report, name='ranking_report'),
    
    # Attendance Reports
    path('attendance/', views.attendance_report, name='attendance_report'),
    path('attendance/student/<int:student_id>/', views.student_attendance_report, name='student_attendance_report'),
    path('attendance/monthly/<int:year>/<int:month>/', views.monthly_attendance_summary, name='monthly_attendance_summary'),
    
    # Finance Reports
    path('finance/statement/<int:student_id>/', views.fee_statement, name='fee_statement'),
    path('finance/collections/', views.collection_report, name='collection_report'),
    path('finance/outstanding/', views.outstanding_report, name='outstanding_report'),
    path('finance/budget/<int:year>/', views.budget_report, name='budget_report'),
    
    # Teacher Reports
    path('teacher/<int:teacher_id>/', views.teacher_report, name='teacher_report'),
    path('teacher-list/', views.teacher_list_report, name='teacher_list_report'),
    
    # Custom Reports
    path('custom/', views.custom_report, name='custom_report'),
]