from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Count, Avg, Sum
from django.core.paginator import Paginator
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.views.decorators.http import require_POST
from accounts.decorators import role_required, teacher_required, admin_required
from .models import (
    Student, Parent, StudentDocument, Club, Sport, 
    ClubMembership, SportParticipation, StudentNote
)
from .forms import (
    StudentForm, StudentSearchForm, ParentForm, StudentDocumentForm,
    ClubForm, SportForm, StudentNoteForm, StudentBulkUploadForm,
    StudentFilterForm, StudentTransferForm, StudentSubjectEnrollmentForm
)
from academics.models import Subject, Result
from finance.models import FeeStructure, Payment, Invoice
from attendance.models import Attendance
import csv
import io
from django.contrib.auth import get_user_model

User = get_user_model()

@login_required
def student_list(request):
    """List all students with filters"""
    students = Student.objects.select_related('user').all()
    
    # Apply filters
    form = StudentFilterForm(request.GET)
    if form.is_valid():
        if form.cleaned_data.get('class_level'):
            students = students.filter(current_class__in=form.cleaned_data['class_level'])
        if form.cleaned_data.get('stream'):
            students = students.filter(stream__in=form.cleaned_data['stream'])
        if form.cleaned_data.get('gender'):
            students = students.filter(gender=form.cleaned_data['gender'])
        if form.cleaned_data.get('boarding_status'):
            students = students.filter(boarding_status=form.cleaned_data['boarding_status'])
        if form.cleaned_data.get('year_of_admission'):
            students = students.filter(year_of_admission=form.cleaned_data['year_of_admission'])
        if form.cleaned_data.get('is_active') is not None:
            students = students.filter(is_active=form.cleaned_data['is_active'])
    
    # Search
    search_query = request.GET.get('search', '')
    if search_query:
        students = students.filter(
            Q(admission_number__icontains=search_query) |
            Q(kcpe_index__icontains=search_query) |
            Q(user__first_name__icontains=search_query) |
            Q(user__last_name__icontains=search_query) |
            Q(parent_name__icontains=search_query)
        )
    
    # Statistics
    total_students = students.count()
    active_students = students.filter(is_active=True).count()
    male_count = students.filter(gender='M').count()
    female_count = students.filter(gender='F').count()
    
    # Class distribution
    class_distribution = students.values('current_class').annotate(
        count=Count('id')
    ).order_by('current_class')
    
    # Pagination
    paginator = Paginator(students, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'form': form,
        'total_students': total_students,
        'active_students': active_students,
        'male_count': male_count,
        'female_count': female_count,
        'class_distribution': class_distribution,
    }
    
    return render(request, 'students/student_list.html', context)

@login_required
def student_detail(request, student_id):
    """View student details"""
    student = get_object_or_404(Student.objects.select_related('user'), id=student_id)
    
    # Get related data
    documents = student.documents.all()
    notes = student.notes.all().order_by('-created_at')[:5]
    parents = student.parents.all()
    clubs = student.clubs.all()
    sports = student.sports.all()
    
    # Get academic data
    results = Result.objects.filter(student=student).select_related('subject', 'term').order_by('-term__year', '-term__term')[:10]
    
    # Get attendance data
    attendance = Attendance.objects.filter(student=student).order_by('-date')[:30]
    attendance_percentage = student.get_attendance_percentage()
    
    # Get financial data
    invoices = Invoice.objects.filter(student=student).order_by('-created_at')[:5]
    total_paid = Payment.objects.filter(student=student).aggregate(total=Sum('amount'))['total'] or 0
    outstanding_balance = student.get_outstanding_balance()
    
    context = {
        'student': student,
        'documents': documents,
        'notes': notes,
        'parents': parents,
        'clubs': clubs,
        'sports': sports,
        'results': results,
        'attendance': attendance,
        'attendance_percentage': attendance_percentage,
        'invoices': invoices,
        'total_paid': total_paid,
        'outstanding_balance': outstanding_balance,
    }
    
    return render(request, 'students/student_detail.html', context)

@login_required
@admin_required
def student_create(request):
    """Create new student"""
    if request.method == 'POST':
        form = StudentForm(request.POST, request.FILES, request=request)
        if form.is_valid():
            student = form.save()
            
            # Create audit log
            from accounts.models import AuditLog
            AuditLog.objects.create(
                user=request.user,
                action='CREATE',
                model_name='Student',
                object_id=student.id,
                object_repr=str(student),
                ip_address=request.META.get('REMOTE_ADDR')
            )
            
            messages.success(request, f'Student {student.get_full_name()} created successfully.')
            return redirect('students:detail', student_id=student.id)
    else:
        form = StudentForm(request=request)
    
    return render(request, 'students/student_form.html', {
        'form': form,
        'title': 'Add New Student'
    })

@login_required
@admin_required
def student_edit(request, student_id):
    """Edit student"""
    student = get_object_or_404(Student, id=student_id)
    
    if request.method == 'POST':
        form = StudentForm(request.POST, request.FILES, instance=student, request=request)
        if form.is_valid():
            student = form.save()
            
            # Create audit log
            from accounts.models import AuditLog
            AuditLog.objects.create(
                user=request.user,
                action='UPDATE',
                model_name='Student',
                object_id=student.id,
                object_repr=str(student),
                ip_address=request.META.get('REMOTE_ADDR')
            )
            
            messages.success(request, f'Student {student.get_full_name()} updated successfully.')
            return redirect('students:detail', student_id=student.id)
    else:
        form = StudentForm(instance=student, request=request)
    
    return render(request, 'students/student_form.html', {
        'form': form,
        'student': student,
        'title': f'Edit Student: {student.get_full_name()}'
    })

@login_required
@admin_required
def student_delete(request, student_id):
    """Delete student"""
    student = get_object_or_404(Student, id=student_id)
    
    if request.method == 'POST':
        full_name = student.get_full_name()
        
        # Create audit log before deletion
        from accounts.models import AuditLog
        AuditLog.objects.create(
            user=request.user,
            action='DELETE',
            model_name='Student',
            object_id=student.id,
            object_repr=str(student),
            ip_address=request.META.get('REMOTE_ADDR')
        )
        
        student.delete()
        messages.success(request, f'Student {full_name} deleted successfully.')
        return redirect('students:list')
    
    return render(request, 'students/student_confirm_delete.html', {'student': student})

@login_required
def student_dashboard(request):
    """Student's personal dashboard"""
    # First check if the user is actually a student
    if request.user.role != 'student':
        messages.error(request, 'Access denied. This dashboard is only for students.')
        return redirect('dashboard:home')
    
    # Try to get the student profile
    try:
        student = request.user.student_profile
    except Student.DoesNotExist:
        messages.error(request, 'Student profile not found. Please contact administrator.')
        return redirect('dashboard:home')
    
    # Get current term results
    from academics.models import AcademicYear, Term, Result
    current_year = AcademicYear.objects.filter(is_current=True).first()
    current_term = Term.objects.filter(academic_year=current_year, is_current=True).first()
    
    if current_term:
        results = Result.objects.filter(student=student, exam__term=current_term).select_related('subject')
        total_marks = sum(r.marks for r in results)
        average = total_marks / len(results) if results else 0
    else:
        results = []
        average = 0
    
    # Get attendance for current term
    from attendance.models import Attendance
    attendance = Attendance.objects.filter(
        student=student,
        date__gte=current_term.start_date if current_term else None,
        date__lte=current_term.end_date if current_term else None
    )
    total_days = attendance.count()
    present_days = attendance.filter(status='present').count()
    attendance_percentage = (present_days / total_days * 100) if total_days > 0 else 0
    
    # Get financial summary
    from finance.models import Invoice, Payment
    from django.db.models import Sum
    invoices = Invoice.objects.filter(student=student).order_by('-created_at')[:5]
    total_paid = Payment.objects.filter(student=student, payment_status='completed').aggregate(total=Sum('amount'))['total'] or 0
    
    # Get upcoming events
    from academics.models import Exam
    upcoming_exams = Exam.objects.filter(
        term=current_term,
        date__gte=timezone.now().date()
    ).order_by('date')[:5]
    
    context = {
        'student': student,
        'current_term': current_term,
        'results': results,
        'average': average,
        'attendance_percentage': attendance_percentage,
        'present_days': present_days,
        'total_days': total_days,
        'invoices': invoices,
        'total_paid': total_paid,
        'upcoming_exams': upcoming_exams,
        'clubs': student.clubs.all(),
        'sports': student.sports.all(),
    }
    
    return render(request, 'students/dashboard.html', context)

@login_required
def student_subjects(request, student_id):
    """View and manage student subjects"""
    student = get_object_or_404(Student, id=student_id)
    
    # Check permission
    if not (request.user.is_admin() or request.user.is_teacher() or request.user == student.user):
        messages.error(request, 'You do not have permission to view this page.')
        return redirect('dashboard:home')
    
    if request.method == 'POST':
        form = StudentSubjectEnrollmentForm(request.POST, student=student)
        if form.is_valid():
            # Update subjects
            student.subjects.set(form.cleaned_data['subjects'])
            messages.success(request, 'Subjects updated successfully.')
            return redirect('students:detail', student_id=student.id)
    else:
        form = StudentSubjectEnrollmentForm(student=student)
    
    return render(request, 'students/student_subjects.html', {
        'student': student,
        'form': form
    })

@login_required
def student_attendance(request, student_id):
    """View student attendance"""
    student = get_object_or_404(Student, id=student_id)
    
    # Check permission
    if not (request.user.is_admin() or request.user.is_teacher() or request.user == student.user):
        messages.error(request, 'You do not have permission to view this page.')
        return redirect('dashboard:home')
    
    # Get date range
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    attendance = Attendance.objects.filter(student=student)
    
    if start_date:
        attendance = attendance.filter(date__gte=start_date)
    if end_date:
        attendance = attendance.filter(date__lte=end_date)
    
    attendance = attendance.order_by('-date')
    
    # Calculate statistics
    total_days = attendance.count()
    present_days = attendance.filter(status='present').count()
    absent_days = attendance.filter(status='absent').count()
    late_days = attendance.filter(status='late').count()
    excused_days = attendance.filter(status='excused').count()
    
    context = {
        'student': student,
        'attendance': attendance,
        'total_days': total_days,
        'present_days': present_days,
        'absent_days': absent_days,
        'late_days': late_days,
        'excused_days': excused_days,
        'attendance_percentage': (present_days / total_days * 100) if total_days > 0 else 0,
    }
    
    return render(request, 'students/student_attendance.html', context)

@login_required
def student_results(request, student_id):
    """View student results"""
    student = get_object_or_404(Student, id=student_id)
    
    # Check permission
    if not (request.user.is_admin() or request.user.is_teacher() or request.user == student.user):
        messages.error(request, 'You do not have permission to view this page.')
        return redirect('dashboard:home')
    
    # Get results grouped by term
    results = Result.objects.filter(student=student).select_related('subject', 'term')
    
    # Group by term
    terms = {}
    for result in results:
        term_key = f"{result.term.academic_year.name} - {result.term.get_term_display()}"
        if term_key not in terms:
            terms[term_key] = {
                'term': result.term,
                'results': [],
                'total': 0,
                'count': 0
            }
        terms[term_key]['results'].append(result)
        terms[term_key]['total'] += result.marks
        terms[term_key]['count'] += 1
    
    # Calculate averages
    for term_data in terms.values():
        term_data['average'] = term_data['total'] / term_data['count'] if term_data['count'] > 0 else 0
    
    context = {
        'student': student,
        'terms': terms,
    }
    
    return render(request, 'students/student_results.html', context)

@login_required
@require_POST
def student_add_note(request, student_id):
    """Add a note to student"""
    student = get_object_or_404(Student, id=student_id)
    
    form = StudentNoteForm(request.POST)
    if form.is_valid():
        note = form.save(commit=False)
        note.student = student
        note.created_by = request.user
        note.save()
        
        messages.success(request, 'Note added successfully.')
    else:
        messages.error(request, 'Error adding note. Please check the form.')
    
    return redirect('students:detail', student_id=student.id)

@login_required
def student_documents(request, student_id):
    """View student documents"""
    student = get_object_or_404(Student, id=student_id)
    documents = student.documents.all().order_by('-uploaded_at')
    
    return render(request, 'students/student_documents.html', {
        'student': student,
        'documents': documents
    })

@login_required
def student_document_upload(request, student_id):
    """Upload document for student"""
    student = get_object_or_404(Student, id=student_id)
    
    if request.method == 'POST':
        form = StudentDocumentForm(request.POST, request.FILES)
        if form.is_valid():
            document = form.save(commit=False)
            document.student = student
            document.uploaded_by = request.user
            document.save()
            
            messages.success(request, 'Document uploaded successfully.')
            return redirect('students:documents', student_id=student.id)
    else:
        form = StudentDocumentForm()
    
    return render(request, 'students/document_upload.html', {
        'student': student,
        'form': form
    })

@login_required
def student_document_delete(request, document_id):
    """Delete student document"""
    document = get_object_or_404(StudentDocument, id=document_id)
    student_id = document.student.id
    
    if request.method == 'POST':
        document.file.delete()  # Delete the file
        document.delete()
        messages.success(request, 'Document deleted successfully.')
    
    return redirect('students:documents', student_id=student_id)

@login_required
@admin_required
def student_bulk_upload(request):
    """Bulk upload students via CSV"""
    if request.method == 'POST':
        form = StudentBulkUploadForm(request.POST, request.FILES)
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
                        password='Student@123',  # Default password
                        first_name=row['first_name'],
                        last_name=row['last_name'],
                        role='student'
                    )
                    
                    # Create student
                    student = Student(
                        user=user,
                        admission_number=row['admission_number'],
                        kcpe_index=row['kcpe_index'],
                        kcpe_marks=int(row['kcpe_marks']),
                        date_of_birth=row['date_of_birth'],
                        gender=row['gender'],
                        current_class=int(row['current_class']),
                        stream=row['stream'],
                        admission_class=int(row['admission_class']),
                        year_of_admission=int(row.get('year_of_admission', timezone.now().year)),
                        parent_name=row['parent_name'],
                        parent_phone=row['parent_phone'],
                        emergency_contact_name=row['emergency_contact_name'],
                        emergency_contact_phone=row['emergency_contact_phone'],
                        emergency_contact_relationship=row.get('emergency_contact_relationship', ''),
                        created_by=request.user
                    )
                    student.save()
                    success_count += 1
                    
                except Exception as e:
                    error_count += 1
                    errors.append(f"Row {success_count + error_count}: {str(e)}")
            
            messages.success(request, f'Successfully imported {success_count} students. {error_count} errors.')
            if errors:
                request.session['import_errors'] = errors
            
            return redirect('students:list')
    else:
        form = StudentBulkUploadForm()
    
    return render(request, 'students/bulk_upload.html', {'form': form})

@login_required
def student_transfer(request, student_id):
    """Transfer student to different class/stream"""
    student = get_object_or_404(Student, id=student_id)
    
    if request.method == 'POST':
        form = StudentTransferForm(request.POST, student=student)
        if form.is_valid():
            old_class = student.get_current_class_name()
            student.current_class = form.cleaned_data['new_class']
            student.stream = form.cleaned_data['new_stream']
            student.save()
            
            # Create note about transfer
            StudentNote.objects.create(
                student=student,
                note_type='academic',
                title='Class Transfer',
                content=f"Student transferred from {old_class} to {student.get_current_class_name()}. Reason: {form.cleaned_data['reason']}",
                created_by=request.user
            )
            
            messages.success(request, f'Student transferred to {student.get_current_class_name()} successfully.')
            return redirect('students:detail', student_id=student.id)
    else:
        form = StudentTransferForm(student=student)
    
    return render(request, 'students/student_transfer.html', {
        'student': student,
        'form': form
    })

@login_required
def export_students(request):
    """Export students list to CSV"""
    students = Student.objects.select_related('user').all()
    
    # Create CSV response
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="students.csv"'
    
    writer = csv.writer(response)
    writer.writerow([
        'Admission Number', 'KCPE Index', 'Full Name', 'Gender',
        'Current Class', 'Stream', 'Parent Name', 'Parent Phone',
        'Boarding Status', 'Is Active'
    ])
    
    for student in students:
        writer.writerow([
            student.admission_number,
            student.kcpe_index,
            student.get_full_name(),
            student.get_gender_display(),
            student.get_current_class_display(),
            student.get_stream_display(),
            student.parent_name,
            student.parent_phone,
            student.get_boarding_status_display(),
            'Yes' if student.is_active else 'No'
        ])
    
    return response

@login_required
def student_api(request):
    """API endpoint for student data (AJAX)"""
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        students = Student.objects.filter(is_active=True).select_related('user')
        data = []
        for student in students:
            data.append({
                'id': student.id,
                'name': student.get_full_name(),
                'admission_number': student.admission_number,
                'class': student.get_current_class_display(),
                'stream': student.get_stream_display(),
            })
        return JsonResponse(data, safe=False)
    return JsonResponse({'error': 'Invalid request'}, status=400)