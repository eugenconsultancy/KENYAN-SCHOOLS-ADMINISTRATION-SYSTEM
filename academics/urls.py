from django.urls import path
from . import views

app_name = 'academics'

urlpatterns = [
    # Dashboard/Index
    path('', views.subject_list, name='index'),  # Redirect to subject list or create a dashboard
    
    # Academic Years
    path('years/', views.academic_year_list, name='academic_year_list'),
    path('years/create/', views.academic_year_create, name='academic_year_create'),
    path('years/<int:year_id>/edit/', views.academic_year_edit, name='academic_year_edit'),
    path('years/<int:year_id>/delete/', views.academic_year_delete, name='academic_year_delete'),
    
    # Terms
    path('terms/', views.term_list, name='term_list'),
    path('terms/create/', views.term_create, name='term_create'),
    path('terms/<int:term_id>/edit/', views.term_edit, name='term_edit'),
    path('terms/<int:term_id>/set-current/', views.term_set_current, name='term_set_current'),
    
    # Subjects
    path('subjects/', views.subject_list, name='subject_list'),
    path('subjects/create/', views.subject_create, name='subject_create'),
    path('subjects/<int:subject_id>/edit/', views.subject_edit, name='subject_edit'),
    path('subjects/<int:subject_id>/delete/', views.subject_delete, name='subject_delete'),
    
    # Classes
    path('classes/', views.class_list, name='class_list'),
    path('classes/create/', views.class_create, name='class_create'),
    path('classes/<int:class_id>/', views.class_detail, name='class_detail'),
    path('classes/<int:class_id>/edit/', views.class_edit, name='class_edit'),
    
    # Subject Allocations
    path('classes/<int:class_id>/allocations/', views.subject_allocation_list, name='subject_allocation_list'),
    path('classes/<int:class_id>/allocations/create/', views.subject_allocation_create, name='subject_allocation_create'),
    path('allocations/<int:allocation_id>/delete/', views.subject_allocation_delete, name='subject_allocation_delete'),
    
    # Exams
    path('exams/', views.exam_list, name='exam_list'),
    path('exams/create/', views.exam_create, name='exam_create'),
    path('exams/<int:exam_id>/', views.exam_detail, name='exam_detail'),
    path('exams/<int:exam_id>/edit/', views.exam_edit, name='exam_edit'),
    path('exams/<int:exam_id>/schedule/create/', views.exam_schedule_create, name='exam_schedule_create'),
    path('exams/<int:exam_id>/publish/', views.exam_publish, name='exam_publish'),
    
    # Results
    path('results/', views.result_list, name='result_list'),
    path('exams/<int:exam_id>/results/entry/', views.result_entry, name='result_entry'),
    path('exams/<int:exam_id>/results/entry/<int:class_id>/', views.result_entry, name='result_entry_class'),
    path('exams/<int:exam_id>/results/bulk-upload/', views.result_bulk_upload, name='result_bulk_upload'),
    path('students/<int:student_id>/results/', views.student_results, name='student_results'),
    path('classes/<int:class_id>/results/', views.class_results, name='class_results'),
    path('classes/<int:class_id>/results/<int:term_id>/', views.class_results, name='class_results_term'),
    
    # Rankings
    path('rankings/', views.ranking_dashboard, name='ranking_dashboard'),
    path('rankings/class/<int:class_level>/', views.class_ranking, name='class_ranking'),
    path('rankings/class/<int:class_level>/<int:term_id>/', views.class_ranking, name='class_ranking_term'),
    path('rankings/update/<int:term_id>/', views.update_rankings, name='update_rankings'),
    
    # Performance Analysis
    path('analysis/', views.performance_analysis, name='performance_analysis'),
    
    # Homework
    path('homework/', views.homework_list, name='homework_list'),
    path('homework/create/', views.homework_create, name='homework_create'),
    path('homework/<int:homework_id>/', views.homework_detail, name='homework_detail'),
    path('homework/<int:homework_id>/edit/', views.homework_edit, name='homework_edit'),
    path('homework/<int:homework_id>/submit/', views.homework_submit, name='homework_submit'),
    path('submissions/<int:submission_id>/grade/', views.homework_grade, name='homework_grade'),
    
    # API endpoints
    path('api/subjects-for-class/<int:class_level>/', views.get_subjects_for_class, name='api_subjects_for_class'),
    path('api/teachers-for-subject/<int:subject_id>/', views.get_teachers_for_subject, name='api_teachers_for_subject'),
]
