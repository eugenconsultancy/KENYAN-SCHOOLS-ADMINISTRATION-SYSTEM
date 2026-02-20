from django.urls import path
from . import views

app_name = 'attendance'

urlpatterns = [
    # Dashboard
    path('', views.attendance_dashboard, name='attendance_dashboard'),
    
    # Student Attendance
    path('mark/', views.mark_attendance, name='mark_attendance'),
    path('class/<int:class_level>/<str:stream>/', views.class_attendance, name='class_attendance'),
    path('student/<int:student_id>/', views.student_attendance, name='student_attendance'),
    path('edit/<int:attendance_id>/', views.edit_attendance, name='edit_attendance'),
    
    # Teacher Attendance
    path('teacher/mark/', views.teacher_attendance_mark, name='teacher_attendance_mark'),
    path('teacher/list/', views.teacher_attendance_list, name='teacher_attendance_list'),
    
    # Reports
    path('reports/', views.attendance_reports, name='attendance_reports'),
    path('reports/generate/', views.generate_report, name='generate_report'),
    path('reports/download/<int:report_id>/', views.download_report, name='download_report'),
    path('reports/export/csv/', views.export_attendance_csv, name='export_attendance_csv'),
    
    # Holidays
    path('holidays/', views.holiday_list, name='holiday_list'),
    path('holidays/create/', views.holiday_create, name='holiday_create'),
    path('holidays/<int:holiday_id>/edit/', views.holiday_edit, name='holiday_edit'),
    path('holidays/<int:holiday_id>/delete/', views.holiday_delete, name='holiday_delete'),
    
    # Notifications
    path('notifications/send/', views.send_notifications, name='send_notifications'),
    path('notifications/', views.notification_list, name='notification_list'),
    
    # API endpoints
    path('api/get-students/', views.get_students_for_class, name='api_get_students'),
    path('api/summary/', views.get_attendance_summary, name='api_summary'),
]
