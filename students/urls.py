from django.urls import path
from . import views

app_name = 'students'

urlpatterns = [
    # Student list and detail
    path('', views.student_list, name='list'),
    path('api/', views.student_api, name='api'),
    path('export/', views.export_students, name='export'),
    path('bulk-upload/', views.student_bulk_upload, name='bulk_upload'),
    
    # Student CRUD - NOTE: 'create/' MUST come before '<int:student_id>/'
    path('create/', views.student_create, name='create'),
    path('<int:student_id>/', views.student_detail, name='detail'),
    path('<int:student_id>/edit/', views.student_edit, name='edit'),
    path('<int:student_id>/delete/', views.student_delete, name='delete'),
    path('<int:student_id>/transfer/', views.student_transfer, name='transfer'),
    
    # Student dashboards and views
    path('dashboard/', views.student_dashboard, name='dashboard'),
    path('<int:student_id>/subjects/', views.student_subjects, name='subjects'),
    path('<int:student_id>/attendance/', views.student_attendance, name='attendance'),
    path('<int:student_id>/results/', views.student_results, name='results'),
    
    # Documents
    path('<int:student_id>/documents/', views.student_documents, name='documents'),
    path('<int:student_id>/documents/upload/', views.student_document_upload, name='document_upload'),
    path('documents/<int:document_id>/delete/', views.student_document_delete, name='document_delete'),
    
    # Notes
    path('<int:student_id>/notes/add/', views.student_add_note, name='add_note'),
]