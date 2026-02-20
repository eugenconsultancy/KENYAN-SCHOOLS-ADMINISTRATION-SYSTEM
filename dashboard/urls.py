from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.home, name='home'),
    path('admin/', views.admin_dashboard, name='admin'),
    path('teacher/', views.teacher_dashboard, name='teacher'),
    path('student/', views.student_dashboard, name='student'),
    path('parent/', views.parent_dashboard, name='parent'),
    path('accountant/', views.accountant_dashboard, name='accountant'),
    path('api/chart-data/', views.get_chart_data, name='chart_data'),
]