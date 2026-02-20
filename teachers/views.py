from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Count, Avg, Sum
from django.core.paginator import Paginator
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.views.decorators.http import require_POST
from accounts.decorators import role_required, admin_required
from .models import (
    Teacher, TeacherQualification, TeacherSubject, TeacherClass,
    TeacherLeave, TeacherAttendance, TeacherDocument, TeacherPerformance,
    TeacherSalary, TeacherTraining, TeacherAward, TeacherNote
)
from .forms import (
    TeacherForm, TeacherSearchForm, TeacherQualificationForm,
    TeacherSubjectForm, TeacherClassForm, TeacherLeaveForm,
    TeacherAttendanceForm, TeacherDocumentForm, TeacherPerformanceForm,
    TeacherSalaryForm, TeacherTrainingForm, TeacherAwardForm,
    TeacherNoteForm, TeacherFilterForm, TeacherBulkUploadForm
)
from academics.models import Subject, AcademicYear, Term
from django.contrib.auth import get_user_model
import csv
import io

User = get_user_model()

@login_required
@admin_required
def teacher_list(request):
    """List all teachers with filters"""
    teachers = Teacher.objects.select_related('user').all()
    
    # Apply filters
    form = TeacherFilterForm(request.GET)
    if form.is_valid():
        if form.cleaned_data.get('employment_type'):
            teachers = teachers.filter(employment_type__in=form.cleaned_data['employment_type'])
        if form.cleaned_data.get('qualification_level'):
            teachers = teachers.filter(qualification_level__in=form.cleaned_data['qualification_level'])
        if form.cleaned_data.get('gender'):
            teachers = teachers.filter(gender=form.cleaned_data['gender'])
        if form.cleaned_data.get('years_experience_min'):
            teachers = teachers.filter(years_of_experience__gte=form.cleaned_data['years_experience_min'])
        if form.cleaned_data.get('years_experience_max'):
            teachers = teachers.filter(years_of_experience__lte=form.cleaned_data['years_experience_max'])
        if form.cleaned_data.get('is_active') is not None:
            teachers = teachers.filter(is_active=form.cleaned_data['is_active'])
    
    # Search
    search_query = request.GET.get('search', '')
    if search_query:
        teachers = teachers.filter(
            Q(employee_number__icontains=search_query) |
            Q(tsc_number__icontains=search_query) |
            Q(id_number__icontains=search_query) |
            Q(user__first_name__icontains=search_query) |
            Q(user__last_name__icontains=search_query) |
            Q(phone_number__icontains=search_query)
        )
    
    # Statistics
    total_teachers = teachers.count()
    active_teachers = teachers.filter(is_active=True).count()
    male_count = teachers.filter(gender='M').count()
    female_count = teachers.filter(gender='F').count()
    
    # Employment type distribution
    employment_distribution = teachers.values('employment_type').annotate(
        count=Count('id')
    ).order_by('employment_type')
    
    # Pagination
    paginator = Paginator(teachers, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'form': form,
        'total_teachers': total_teachers,
        'active_teachers': active_teachers,
        'male_count': male_count,
        'female_count': female_count,
        'employment_distribution': employment_distribution,
    }
    
    return render(request, 'teachers/teacher_list.html', context)

@login_required
def teacher_detail(request, teacher_id):
    """View teacher details"""
    teacher = get_object_or_404(Teacher.objects.select_related('user'), id=teacher_id)
    
    # Check permission
    if not (request.user.is_admin() or request.user.is_teacher() and request.user.teacher_profile.id == teacher_id):
        messages.error(request, 'You do not have permission to view this page.')
        return redirect('dashboard:home')
    
    # Get related data
    documents = teacher.documents.all()
    notes = teacher.notes.all().order_by('-created_at')[:5]
    subjects = teacher.subjects_taught.select_related('subject').all()
    form_classes = teacher.form_classes.select_related('academic_year').filter(is_current=True)
    
    # Get leave records
    leaves = teacher.leaves.all().order_by('-created_at')[:5]
    
    # Get attendance
    attendance = teacher.attendance_records.all().order_by('-date')[:30]
    
    # Get performance evaluations
    performances = teacher.performances.select_related('term').all()[:3]
    
    # Get qualifications
    qualifications = teacher.additional_qualifications.all()
    
    # Get trainings
    trainings = teacher.trainings.all().order_by('-end_date')[:5]
    
    # Get awards
    awards = teacher.awards.all().order_by('-date_received')[:5]
    
    context = {
        'teacher': teacher,
        'documents': documents,
        'notes': notes,
        'subjects': subjects,
        'form_classes': form_classes,
        'leaves': leaves,
        'attendance': attendance,
        'performances': performances,
        'qualifications': qualifications,
        'trainings': trainings,
        'awards': awards,
    }
    
    return render(request, 'teachers/teacher_detail.html', context)

@login_required
@admin_required
def teacher_create(request):
    """Create new teacher"""
    if request.method == 'POST':
        form = TeacherForm(request.POST, request.FILES, request=request)
        if form.is_valid():
            teacher = form.save()
            
            # Create audit log
            from accounts.models import AuditLog
            AuditLog.objects.create(
                user=request.user,
                action='CREATE',
                model_name='Teacher',
                object_id=teacher.id,
                object_repr=str(teacher),
                ip_address=request.META.get('REMOTE_ADDR')
            )
            
            messages.success(request, f'Teacher {teacher.get_full_name()} created successfully.')
            return redirect('teachers:detail', teacher_id=teacher.id)
    else:
        form = TeacherForm(request=request)
    
    return render(request, 'teachers/teacher_form.html', {
        'form': form,
        'title': 'Add New Teacher'
    })

@login_required
@admin_required
def teacher_edit(request, teacher_id):
    """Edit teacher"""
    teacher = get_object_or_404(Teacher, id=teacher_id)
    
    if request.method == 'POST':
        form = TeacherForm(request.POST, request.FILES, instance=teacher, request=request)
        if form.is_valid():
            teacher = form.save()
            
            # Create audit log
            from accounts.models import AuditLog
            AuditLog.objects.create(
                user=request.user,
                action='UPDATE',
                model_name='Teacher',
                object_id=teacher.id,
                object_repr=str(teacher),
                ip_address=request.META.get('REMOTE_ADDR')
            )
            
            messages.success(request, f'Teacher {teacher.get_full_name()} updated successfully.')
            return redirect('teachers:detail', teacher_id=teacher.id)
    else:
        form = TeacherForm(instance=teacher, request=request)
    
    return render(request, 'teachers/teacher_form.html', {
        'form': form,
        'teacher': teacher,
        'title': f'Edit Teacher: {teacher.get_full_name()}'
    })

@login_required
@admin_required
def teacher_delete(request, teacher_id):
    """Delete teacher"""
    teacher = get_object_or_404(Teacher, id=teacher_id)
    
    if request.method == 'POST':
        full_name = teacher.get_full_name()
        
        # Create audit log before deletion
        from accounts.models import AuditLog
        AuditLog.objects.create(
            user=request.user,
            action='DELETE',
            model_name='Teacher',
            object_id=teacher.id,
            object_repr=str(teacher),
            ip_address=request.META.get('REMOTE_ADDR')
        )
        
        teacher.delete()
        messages.success(request, f'Teacher {full_name} deleted successfully.')
        return redirect('teachers:list')
    
    return render(request, 'teachers/teacher_confirm_delete.html', {'teacher': teacher})

@login_required
def teacher_dashboard(request):
    """Teacher's personal dashboard"""
    if not request.user.is_teacher():
        messages.error(request, 'Access denied. Teacher account required.')
        return redirect('dashboard:home')
    
    try:
        teacher = request.user.teacher_profile
    except Teacher.DoesNotExist:
        messages.error(request, 'Teacher profile not found.')
        return redirect('dashboard:home')
    
    # Get current academic year and term
    from academics.models import AcademicYear, Term
    current_year = AcademicYear.objects.filter(is_current=True).first()
    current_term = Term.objects.filter(academic_year=current_year, is_current=True).first()
    
    # Get assigned classes
    form_classes = teacher.form_classes.filter(is_current=True)
    
    # Get subjects taught
    subjects = teacher.subjects_taught.select_related('subject').all()
    
    # Get today's attendance - try different possible related names
    from attendance.models import TeacherAttendance
    
    # Method 1: Direct filter (most reliable)
    today_attendance = TeacherAttendance.objects.filter(
        teacher=teacher,
        date=timezone.now().date()
    ).first()
    
    # Get pending leave requests
    pending_leaves = teacher.leaves.filter(status='pending').count()
    
    # Get recent attendance records
    recent_attendance = TeacherAttendance.objects.filter(
        teacher=teacher
    ).order_by('-date')[:10]
    
    # Calculate attendance statistics for current month
    current_month_attendance = TeacherAttendance.objects.filter(
        teacher=teacher,
        date__month=timezone.now().month,
        date__year=timezone.now().year
    )
    total_days = current_month_attendance.count()
    present_days = current_month_attendance.filter(status='present').count()
    attendance_percentage = (present_days / total_days * 100) if total_days > 0 else 0
    
    context = {
        'teacher': teacher,
        'form_classes': form_classes,
        'subjects': subjects,
        'today_attendance': today_attendance,
        'pending_leaves': pending_leaves,
        'recent_attendance': recent_attendance,
        'attendance_percentage': attendance_percentage,
        'present_days': present_days,
        'total_days': total_days,
        'current_term': current_term,
    }
    
    return render(request, 'teachers/dashboard.html', context)


@login_required
def teacher_subjects(request, teacher_id):
    """Manage teacher's subjects"""
    teacher = get_object_or_404(Teacher, id=teacher_id)
    
    # Check permission
    if not (request.user.is_admin() or request.user == teacher.user):
        messages.error(request, 'You do not have permission to view this page.')
        return redirect('dashboard:home')
    
    if request.method == 'POST':
        form = TeacherSubjectForm(request.POST)
        if form.is_valid():
            subject_assignment = form.save(commit=False)
            subject_assignment.teacher = teacher
            subject_assignment.save()
            messages.success(request, 'Subject assigned successfully.')
            return redirect('teachers:subjects', teacher_id=teacher.id)
    else:
        form = TeacherSubjectForm()
    
    subjects = teacher.subjects_taught.select_related('subject').all()
    
    context = {
        'teacher': teacher,
        'subjects': subjects,
        'form': form,
    }
    
    return render(request, 'teachers/teacher_subjects.html', context)

@login_required
def teacher_subject_delete(request, subject_id):
    """Remove subject from teacher"""
    subject_assignment = get_object_or_404(TeacherSubject, id=subject_id)
    teacher_id = subject_assignment.teacher.id
    
    if request.method == 'POST':
        subject_assignment.delete()
        messages.success(request, 'Subject removed successfully.')
    
    return redirect('teachers:subjects', teacher_id=teacher_id)

@login_required
def teacher_classes(request, teacher_id):
    """Manage teacher's form classes"""
    teacher = get_object_or_404(Teacher, id=teacher_id)
    
    # Check permission
    if not (request.user.is_admin() or request.user == teacher.user):
        messages.error(request, 'You do not have permission to view this page.')
        return redirect('dashboard:home')
    
    if request.method == 'POST':
        form = TeacherClassForm(request.POST)
        if form.is_valid():
            class_assignment = form.save(commit=False)
            class_assignment.teacher = teacher
            class_assignment.save()
            messages.success(request, 'Class assigned successfully.')
            return redirect('teachers:classes', teacher_id=teacher.id)
    else:
        form = TeacherClassForm()
    
    classes = teacher.form_classes.select_related('academic_year').all()
    
    context = {
        'teacher': teacher,
        'classes': classes,
        'form': form,
    }
    
    return render(request, 'teachers/teacher_classes.html', context)

@login_required
def teacher_class_delete(request, class_id):
    """Remove class from teacher"""
    class_assignment = get_object_or_404(TeacherClass, id=class_id)
    teacher_id = class_assignment.teacher.id
    
    if request.method == 'POST':
        class_assignment.delete()
        messages.success(request, 'Class assignment removed successfully.')
    
    return redirect('teachers:classes', teacher_id=teacher_id)

@login_required
def teacher_leave_list(request):
    """List leave requests for teachers"""
    if request.user.is_admin():
        leaves = TeacherLeave.objects.all().select_related('teacher').order_by('-created_at')
    else:
        teacher = get_object_or_404(Teacher, user=request.user)
        leaves = teacher.leaves.all().order_by('-created_at')
    
    # Filter by status
    status = request.GET.get('status', '')
    if status:
        leaves = leaves.filter(status=status)
    
    paginator = Paginator(leaves, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'status': status,
        'is_admin': request.user.is_admin(),
    }
    
    return render(request, 'teachers/leave_list.html', context)

@login_required
def teacher_leave_create(request):
    """Create leave request"""
    if request.user.is_teacher():
        teacher = get_object_or_404(Teacher, user=request.user)
        
        if request.method == 'POST':
            form = TeacherLeaveForm(request.POST)
            if form.is_valid():
                leave = form.save(commit=False)
                leave.teacher = teacher
                leave.save()
                
                messages.success(request, 'Leave request submitted successfully.')
                return redirect('teachers:leave_list')
        else:
            form = TeacherLeaveForm()
        
        return render(request, 'teachers/leave_form.html', {'form': form})
    else:
        messages.error(request, 'Only teachers can create leave requests.')
        return redirect('teachers:leave_list')

@login_required
@admin_required
def teacher_leave_approve(request, leave_id):
    """Approve or reject leave request"""
    leave = get_object_or_404(TeacherLeave, id=leave_id)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        remarks = request.POST.get('remarks', '')
        
        if action == 'approve':
            leave.status = 'approved'
            leave.approved_by = request.user
            leave.approved_date = timezone.now()
            messages.success(request, 'Leave request approved.')
        elif action == 'reject':
            leave.status = 'rejected'
            leave.approved_by = request.user
            leave.approved_date = timezone.now()
            messages.success(request, 'Leave request rejected.')
        
        leave.remarks = remarks
        leave.save()
    
    return redirect('teachers:leave_list')

@login_required
def teacher_attendance_mark(request):
    """Mark teacher attendance"""
    if not (request.user.is_admin() or request.user.is_teacher()):
        messages.error(request, 'Access denied.')
        return redirect('dashboard:home')
    
    if request.method == 'POST':
        form = TeacherAttendanceForm(request.POST)
        if form.is_valid():
            attendance = form.save(commit=False)
            attendance.marked_by = request.user
            
            # Calculate late minutes if checked in late
            if attendance.check_in_time and attendance.status == 'late':
                # Assuming school starts at 8:00 AM
                school_start = timezone.datetime.strptime('08:00', '%H:%M').time()
                check_in = attendance.check_in_time
                late_minutes = (check_in.hour * 60 + check_in.minute) - (school_start.hour * 60 + school_start.minute)
                attendance.late_minutes = max(0, late_minutes)
            
            attendance.save()
            messages.success(request, 'Attendance marked successfully.')
            return redirect('teachers:attendance_list')
    else:
        form = TeacherAttendanceForm()
        form.fields['teacher'].queryset = Teacher.objects.filter(is_active=True)
    
    return render(request, 'teachers/attendance_form.html', {'form': form})

@login_required
def teacher_attendance_list(request):
    """List teacher attendance records"""
    if request.user.is_admin():
        attendance = TeacherAttendance.objects.all().select_related('teacher').order_by('-date')
    else:
        teacher = get_object_or_404(Teacher, user=request.user)
        attendance = teacher.attendance_records.all().order_by('-date')
    
    # Filter by date
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    if start_date:
        attendance = attendance.filter(date__gte=start_date)
    if end_date:
        attendance = attendance.filter(date__lte=end_date)
    
    paginator = Paginator(attendance, 30)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'start_date': start_date,
        'end_date': end_date,
        'is_admin': request.user.is_admin(),
    }
    
    return render(request, 'teachers/attendance_list.html', context)

@login_required
def teacher_documents(request, teacher_id):
    """View teacher documents"""
    teacher = get_object_or_404(Teacher, id=teacher_id)
    
    # Check permission
    if not (request.user.is_admin() or request.user == teacher.user):
        messages.error(request, 'You do not have permission to view this page.')
        return redirect('dashboard:home')
    
    documents = teacher.documents.all().order_by('-uploaded_at')
    
    # Group by document type
    document_groups = {}
    for doc in documents:
        if doc.document_type not in document_groups:
            document_groups[doc.document_type] = []
        document_groups[doc.document_type].append(doc)
    
    context = {
        'teacher': teacher,
        'document_groups': document_groups,
    }
    
    return render(request, 'teachers/teacher_documents.html', context)

@login_required
def teacher_document_upload(request, teacher_id):
    """Upload document for teacher"""
    teacher = get_object_or_404(Teacher, id=teacher_id)
    
    if request.method == 'POST':
        form = TeacherDocumentForm(request.POST, request.FILES)
        if form.is_valid():
            document = form.save(commit=False)
            document.teacher = teacher
            document.uploaded_by = request.user
            document.save()
            
            messages.success(request, 'Document uploaded successfully.')
            return redirect('teachers:documents', teacher_id=teacher.id)
    else:
        form = TeacherDocumentForm()
    
    return render(request, 'teachers/document_upload.html', {
        'teacher': teacher,
        'form': form
    })

@login_required
def teacher_document_delete(request, document_id):
    """Delete teacher document"""
    document = get_object_or_404(TeacherDocument, id=document_id)
    teacher_id = document.teacher.id
    
    if request.method == 'POST':
        document.file.delete()  # Delete the file
        document.delete()
        messages.success(request, 'Document deleted successfully.')
    
    return redirect('teachers:documents', teacher_id=teacher_id)

@login_required
@admin_required
def teacher_performance_list(request):
    """List teacher performance evaluations"""
    performances = TeacherPerformance.objects.all().select_related('teacher', 'term').order_by('-evaluation_date')
    
    # Filter by term
    term_id = request.GET.get('term')
    if term_id:
        performances = performances.filter(term_id=term_id)
    
    # Filter by teacher
    teacher_id = request.GET.get('teacher')
    if teacher_id:
        performances = performances.filter(teacher_id=teacher_id)
    
    paginator = Paginator(performances, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'terms': Term.objects.all().order_by('-academic_year', '-term'),
        'teachers': Teacher.objects.filter(is_active=True),
    }
    
    return render(request, 'teachers/performance_list.html', context)

@login_required
@admin_required
def teacher_performance_create(request):
    """Create performance evaluation"""
    if request.method == 'POST':
        form = TeacherPerformanceForm(request.POST)
        if form.is_valid():
            performance = form.save(commit=False)
            performance.evaluator = request.user
            performance.save()
            
            messages.success(request, 'Performance evaluation saved successfully.')
            return redirect('teachers:performance_list')
    else:
        form = TeacherPerformanceForm()
        # Set default term to current
        current_term = Term.objects.filter(is_current=True).first()
        if current_term:
            form.fields['term'].initial = current_term.id
    
    return render(request, 'teachers/performance_form.html', {'form': form})

@login_required
@admin_required
def teacher_performance_edit(request, performance_id):
    """Edit performance evaluation"""
    performance = get_object_or_404(TeacherPerformance, id=performance_id)
    
    if request.method == 'POST':
        form = TeacherPerformanceForm(request.POST, instance=performance)
        if form.is_valid():
            form.save()
            messages.success(request, 'Performance evaluation updated successfully.')
            return redirect('teachers:performance_list')
    else:
        form = TeacherPerformanceForm(instance=performance)
    
    return render(request, 'teachers/performance_form.html', {
        'form': form,
        'performance': performance
    })

@login_required
@admin_required
def teacher_salary_list(request):
    """List teacher salary records"""
    salaries = TeacherSalary.objects.all().select_related('teacher').order_by('-year', '-month')
    
    # Filter by year
    year = request.GET.get('year')
    if year:
        salaries = salaries.filter(year=year)
    
    # Filter by month
    month = request.GET.get('month')
    if month:
        salaries = salaries.filter(month=month)
    
    paginator = Paginator(salaries, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get available years for filter
    available_years = TeacherSalary.objects.dates('payment_date', 'year').distinct()
    
    context = {
        'page_obj': page_obj,
        'available_years': available_years,
        'current_year': year,
        'current_month': month,
    }
    
    return render(request, 'teachers/salary_list.html', context)

@login_required
@admin_required
def teacher_salary_create(request):
    """Create salary record"""
    if request.method == 'POST':
        form = TeacherSalaryForm(request.POST, request.FILES)
        if form.is_valid():
            salary = form.save()
            messages.success(request, 'Salary record created successfully.')
            return redirect('teachers:salary_list')
    else:
        form = TeacherSalaryForm()
    
    return render(request, 'teachers/salary_form.html', {'form': form})

@login_required
def teacher_salary_detail(request, salary_id):
    """View salary details"""
    salary = get_object_or_404(TeacherSalary, id=salary_id)
    
    # Check permission
    if not (request.user.is_admin() or request.user == salary.teacher.user):
        messages.error(request, 'You do not have permission to view this page.')
        return redirect('dashboard:home')
    
    return render(request, 'teachers/salary_detail.html', {'salary': salary})

@login_required
@admin_required
def teacher_trainings(request, teacher_id):
    """View teacher trainings"""
    teacher = get_object_or_404(Teacher, id=teacher_id)
    trainings = teacher.trainings.all().order_by('-end_date')
    
    if request.method == 'POST':
        form = TeacherTrainingForm(request.POST, request.FILES)
        if form.is_valid():
            training = form.save(commit=False)
            training.teacher = teacher
            training.save()
            messages.success(request, 'Training record added successfully.')
            return redirect('teachers:trainings', teacher_id=teacher.id)
    else:
        form = TeacherTrainingForm()
    
    context = {
        'teacher': teacher,
        'trainings': trainings,
        'form': form,
    }
    
    return render(request, 'teachers/teacher_trainings.html', context)

@login_required
@admin_required
def teacher_awards(request, teacher_id):
    """View teacher awards"""
    teacher = get_object_or_404(Teacher, id=teacher_id)
    awards = teacher.awards.all().order_by('-date_received')
    
    if request.method == 'POST':
        form = TeacherAwardForm(request.POST, request.FILES)
        if form.is_valid():
            award = form.save(commit=False)
            award.teacher = teacher
            award.save()
            messages.success(request, 'Award record added successfully.')
            return redirect('teachers:awards', teacher_id=teacher.id)
    else:
        form = TeacherAwardForm()
    
    context = {
        'teacher': teacher,
        'awards': awards,
        'form': form,
    }
    
    return render(request, 'teachers/teacher_awards.html', context)

@login_required
@require_POST
def teacher_add_note(request, teacher_id):
    """Add a note to teacher"""
    teacher = get_object_or_404(Teacher, id=teacher_id)
    
    form = TeacherNoteForm(request.POST)
    if form.is_valid():
        note = form.save(commit=False)
        note.teacher = teacher
        note.created_by = request.user
        note.save()
        
        messages.success(request, 'Note added successfully.')
    else:
        messages.error(request, 'Error adding note. Please check the form.')
    
    return redirect('teachers:detail', teacher_id=teacher.id)

@login_required
@admin_required
def teacher_bulk_upload(request):
    """Bulk upload teachers via CSV"""
    if request.method == 'POST':
        form = TeacherBulkUploadForm(request.POST, request.FILES)
        if form.is_valid():
            csv_file = request.FILES['csv_file']
            decoded_file = csv_file.read().decode('utf-8')
            io_string = io.StringIO(decoded_file)
            reader = csv.DictReader(io_string)
            
            success_count = 0
            error_count = 0
            errors = []
            
            for row in reader:
                try:
                    # Create user account
                    user = User.objects.create_user(
                        username=row['username'],
                        email=row.get('email', ''),
                        password='Teacher@123',  # Default password
                        first_name=row['first_name'],
                        last_name=row['last_name'],
                        role='teacher'
                    )
                    
                    # Create teacher
                    teacher = Teacher(
                        user=user,
                        employee_number=row['employee_number'],
                        tsc_number=row['tsc_number'],
                        id_number=row['id_number'],
                        date_of_birth=row['date_of_birth'],
                        gender=row['gender'],
                        marital_status=row.get('marital_status', 'single'),
                        qualification_level=row['qualification_level'],
                        qualifications=row.get('qualifications', ''),
                        years_of_experience=int(row.get('years_of_experience', 0)),
                        date_employed=row['date_employed'],
                        employment_type=row.get('employment_type', 'permanent'),
                        phone_number=row['phone_number'],
                        email=row['email'],
                        emergency_contact_name=row['emergency_contact_name'],
                        emergency_contact_phone=row['emergency_contact_phone'],
                        emergency_contact_relationship=row.get('emergency_contact_relationship', ''),
                        created_by=request.user
                    )
                    teacher.save()
                    success_count += 1
                    
                except Exception as e:
                    error_count += 1
                    errors.append(f"Row {success_count + error_count}: {str(e)}")
            
            messages.success(request, f'Successfully imported {success_count} teachers. {error_count} errors.')
            if errors:
                request.session['import_errors'] = errors
            
            return redirect('teachers:list')
    else:
        form = TeacherBulkUploadForm()
    
    return render(request, 'teachers/bulk_upload.html', {'form': form})

@login_required
def export_teachers(request):
    """Export teachers list to CSV"""
    teachers = Teacher.objects.select_related('user').all()
    
    # Create CSV response
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="teachers.csv"'
    
    writer = csv.writer(response)
    writer.writerow([
        'Employee Number', 'TSC Number', 'Full Name', 'Gender',
        'Qualification', 'Employment Type', 'Phone Number', 'Email',
        'Years of Experience', 'Status'
    ])
    
    for teacher in teachers:
        writer.writerow([
            teacher.employee_number,
            teacher.tsc_number,
            teacher.get_full_name(),
            teacher.get_gender_display(),
            teacher.get_qualification_level_display(),
            teacher.get_employment_type_display(),
            teacher.phone_number,
            teacher.email,
            teacher.years_of_experience,
            'Active' if teacher.is_active else 'Inactive'
        ])
    
    return response

@login_required
def teacher_api(request):
    """API endpoint for teacher data (AJAX)"""
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        teachers = Teacher.objects.filter(is_active=True).select_related('user')
        data = []
        for teacher in teachers:
            data.append({
                'id': teacher.id,
                'name': teacher.get_full_name(),
                'employee_number': teacher.employee_number,
                'tsc_number': teacher.tsc_number,
                'phone': teacher.phone_number,
            })
        return JsonResponse(data, safe=False)
    return JsonResponse({'error': 'Invalid request'}, status=400)