from django.urls import path
from . import views

app_name = 'teachers'

urlpatterns = [
    # Teacher list and detail
    path('', views.teacher_list, name='list'),
    path('api/', views.teacher_api, name='api'),
    path('export/', views.export_teachers, name='export'),
    path('bulk-upload/', views.teacher_bulk_upload, name='bulk_upload'),
    
    # Teacher CRUD
    path('create/', views.teacher_create, name='create'),
    path('<int:teacher_id>/', views.teacher_detail, name='detail'),
    path('<int:teacher_id>/edit/', views.teacher_edit, name='edit'),
    path('<int:teacher_id>/delete/', views.teacher_delete, name='delete'),
    
    # Teacher dashboards
    path('dashboard/', views.teacher_dashboard, name='dashboard'),
    
    # Subjects management
    path('<int:teacher_id>/subjects/', views.teacher_subjects, name='subjects'),
    path('subjects/<int:subject_id>/delete/', views.teacher_subject_delete, name='subject_delete'),
    
    # Class management
    path('<int:teacher_id>/classes/', views.teacher_classes, name='classes'),
    path('classes/<int:class_id>/delete/', views.teacher_class_delete, name='class_delete'),
    
    # Leave management
    path('leaves/', views.teacher_leave_list, name='leave_list'),
    path('leaves/create/', views.teacher_leave_create, name='leave_create'),
    path('leaves/<int:leave_id>/approve/', views.teacher_leave_approve, name='leave_approve'),
    
    # Attendance
    path('attendance/mark/', views.teacher_attendance_mark, name='attendance_mark'),
    path('attendance/', views.teacher_attendance_list, name='attendance_list'),
    
    # Documents
    path('<int:teacher_id>/documents/', views.teacher_documents, name='documents'),
    path('<int:teacher_id>/documents/upload/', views.teacher_document_upload, name='document_upload'),
    path('documents/<int:document_id>/delete/', views.teacher_document_delete, name='document_delete'),
    
    # Performance evaluations
    path('performance/', views.teacher_performance_list, name='performance_list'),
    path('performance/create/', views.teacher_performance_create, name='performance_create'),
    path('performance/<int:performance_id>/edit/', views.teacher_performance_edit, name='performance_edit'),
    
    # Salary
    path('salary/', views.teacher_salary_list, name='salary_list'),
    path('salary/create/', views.teacher_salary_create, name='salary_create'),
    path('salary/<int:salary_id>/', views.teacher_salary_detail, name='salary_detail'),
    
    # Trainings and awards
    path('<int:teacher_id>/trainings/', views.teacher_trainings, name='trainings'),
    path('<int:teacher_id>/awards/', views.teacher_awards, name='awards'),
    
    # Notes
    path('<int:teacher_id>/notes/add/', views.teacher_add_note, name='add_note'),
]