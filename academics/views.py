from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import models
from django.db.models import Q, Count, Avg, Sum
from django.core.paginator import Paginator
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from accounts.decorators import role_required, teacher_required, admin_required
from .models import (
    AcademicYear, Term, Subject, SubjectCategory, Class,
    SubjectAllocation, Exam, ExamSchedule, Result, ResultSummary,
    Timetable, LessonPlan, Homework, HomeworkSubmission
)
from .forms import (
    AcademicYearForm, TermForm, SubjectForm, SubjectCategoryForm,
    ClassForm, SubjectAllocationForm, ExamForm, ExamScheduleForm,
    ResultForm, ResultBulkUploadForm, TimetableForm, LessonPlanForm,
    HomeworkForm, HomeworkSubmissionForm
)
from students.models import Student
from teachers.models import Teacher
from .grading import GradingSystem, ReportCardGenerator, RankCalculator
from .ranking import RankingService, PerformanceAnalyzer
import csv
import io

# ============== Academic Year Views ==============

@login_required
@admin_required
def academic_year_list(request):
    """List all academic years"""
    years = AcademicYear.objects.all().order_by('-start_date')
    
    context = {
        'years': years,
    }
    return render(request, 'academics/academic_year_list.html', context)

@login_required
@admin_required
def academic_year_create(request):
    """Create new academic year"""
    if request.method == 'POST':
        form = AcademicYearForm(request.POST)
        if form.is_valid():
            year = form.save()
            messages.success(request, f'Academic year {year.name} created successfully.')
            return redirect('academics:academic_year_list')
    else:
        form = AcademicYearForm()
    
    return render(request, 'academics/academic_year_form.html', {
        'form': form,
        'title': 'Create Academic Year'
    })

@login_required
@admin_required
def academic_year_edit(request, year_id):
    """Edit academic year"""
    year = get_object_or_404(AcademicYear, id=year_id)
    
    if request.method == 'POST':
        form = AcademicYearForm(request.POST, instance=year)
        if form.is_valid():
            form.save()
            messages.success(request, 'Academic year updated successfully.')
            return redirect('academics:academic_year_list')
    else:
        form = AcademicYearForm(instance=year)
    
    return render(request, 'academics/academic_year_form.html', {
        'form': form,
        'title': 'Edit Academic Year'
    })

@login_required
@admin_required
def academic_year_delete(request, year_id):
    """Delete academic year"""
    year = get_object_or_404(AcademicYear, id=year_id)
    
    if request.method == 'POST':
        year.delete()
        messages.success(request, 'Academic year deleted successfully.')
        return redirect('academics:academic_year_list')
    
    return render(request, 'academics/academic_year_confirm_delete.html', {'year': year})

# ============== Term Views ==============

@login_required
def term_list(request):
    """List all terms"""
    terms = Term.objects.all().select_related('academic_year').order_by('-academic_year', 'term')
    
    context = {
        'terms': terms,
    }
    return render(request, 'academics/term_list.html', context)

@login_required
@admin_required
def term_create(request):
    """Create new term"""
    if request.method == 'POST':
        form = TermForm(request.POST)
        if form.is_valid():
            term = form.save()
            messages.success(request, f'Term created successfully.')
            return redirect('academics:term_list')
    else:
        form = TermForm()
    
    return render(request, 'academics/term_form.html', {
        'form': form,
        'title': 'Create Term'
    })

@login_required
@admin_required
def term_edit(request, term_id):
    """Edit term"""
    term = get_object_or_404(Term, id=term_id)
    
    if request.method == 'POST':
        form = TermForm(request.POST, instance=term)
        if form.is_valid():
            form.save()
            messages.success(request, 'Term updated successfully.')
            return redirect('academics:term_list')
    else:
        form = TermForm(instance=term)
    
    return render(request, 'academics/term_form.html', {
        'form': form,
        'title': 'Edit Term'
    })

@login_required
@admin_required
def term_set_current(request, term_id):
    """Set current term"""
    term = get_object_or_404(Term, id=term_id)
    term.is_current = True
    term.save()
    messages.success(request, f'{term} set as current term.')
    return redirect('academics:term_list')

# ============== Subject Views ==============

@login_required
def subject_list(request):
    """List all subjects"""
    subjects = Subject.objects.all().select_related('category').order_by('category', 'name')
    
    # Filter by category
    category_id = request.GET.get('category')
    if category_id:
        subjects = subjects.filter(category_id=category_id)
    
    # Filter by type
    subject_type = request.GET.get('type')
    if subject_type:
        subjects = subjects.filter(subject_type=subject_type)
    
    categories = SubjectCategory.objects.all()
    
    context = {
        'subjects': subjects,
        'categories': categories,
        'subject_types': Subject.SUBJECT_TYPES,
    }
    return render(request, 'academics/subject_list.html', context)

@login_required
@admin_required
def subject_create(request):
    """Create new subject"""
    if request.method == 'POST':
        form = SubjectForm(request.POST)
        if form.is_valid():
            subject = form.save()
            messages.success(request, f'Subject {subject.name} created successfully.')
            return redirect('academics:subject_list')
    else:
        form = SubjectForm()
    
    return render(request, 'academics/subject_form.html', {
        'form': form,
        'title': 'Create Subject'
    })

@login_required
@admin_required
def subject_edit(request, subject_id):
    """Edit subject"""
    subject = get_object_or_404(Subject, id=subject_id)
    
    if request.method == 'POST':
        form = SubjectForm(request.POST, instance=subject)
        if form.is_valid():
            form.save()
            messages.success(request, 'Subject updated successfully.')
            return redirect('academics:subject_list')
    else:
        form = SubjectForm(instance=subject)
    
    return render(request, 'academics/subject_form.html', {
        'form': form,
        'title': 'Edit Subject'
    })

@login_required
@admin_required
def subject_delete(request, subject_id):
    """Delete subject"""
    subject = get_object_or_404(Subject, id=subject_id)
    
    if request.method == 'POST':
        subject.delete()
        messages.success(request, 'Subject deleted successfully.')
        return redirect('academics:subject_list')
    
    return render(request, 'academics/subject_confirm_delete.html', {'subject': subject})

# ============== Class Views ==============

@login_required
def class_list(request):
    """List all classes"""
    classes = Class.objects.all().select_related('academic_year', 'class_teacher').order_by('academic_year', 'class_level', 'stream')
    
    # Filter by academic year
    year_id = request.GET.get('year')
    if year_id:
        classes = classes.filter(academic_year_id=year_id)
    
    academic_years = AcademicYear.objects.all()
    
    context = {
        'classes': classes,
        'academic_years': academic_years,
    }
    return render(request, 'academics/class_list.html', context)

@login_required
@admin_required
def class_create(request):
    """Create new class"""
    if request.method == 'POST':
        form = ClassForm(request.POST)
        if form.is_valid():
            class_obj = form.save()
            messages.success(request, f'Class {class_obj} created successfully.')
            return redirect('academics:class_list')
    else:
        form = ClassForm()
    
    return render(request, 'academics/class_form.html', {
        'form': form,
        'title': 'Create Class'
    })

@login_required
@admin_required
def class_edit(request, class_id):
    """Edit class"""
    class_obj = get_object_or_404(Class, id=class_id)
    
    if request.method == 'POST':
        form = ClassForm(request.POST, instance=class_obj)
        if form.is_valid():
            form.save()
            messages.success(request, 'Class updated successfully.')
            return redirect('academics:class_list')
    else:
        form = ClassForm(instance=class_obj)
    
    return render(request, 'academics/class_form.html', {
        'form': form,
        'title': 'Edit Class'
    })

@login_required
@admin_required
def class_detail(request, class_id):
    """View class details"""
    class_obj = get_object_or_404(Class, id=class_id)
    students = Student.objects.filter(current_class=class_obj.class_level, stream=class_obj.stream, is_active=True)
    subjects = SubjectAllocation.objects.filter(class_assigned=class_obj).select_related('subject', 'teacher')
    
    # Get current term
    current_term = Term.objects.filter(academic_year=class_obj.academic_year, is_current=True).first()
    
    context = {
        'class_obj': class_obj,
        'students': students,
        'subjects': subjects,
        'student_count': students.count(),
        'current_term': current_term,
    }
    return render(request, 'academics/class_detail.html', context)

# ============== Subject Allocation Views ==============

@login_required
@admin_required
def subject_allocation_list(request, class_id):
    """List subject allocations for a class"""
    class_obj = get_object_or_404(Class, id=class_id)
    allocations = SubjectAllocation.objects.filter(class_assigned=class_obj).select_related('subject', 'teacher')
    
    context = {
        'class_obj': class_obj,
        'allocations': allocations,
    }
    return render(request, 'academics/subject_allocation_list.html', context)

@login_required
@admin_required
def subject_allocation_create(request, class_id):
    """Create subject allocation"""
    class_obj = get_object_or_404(Class, id=class_id)
    
    if request.method == 'POST':
        form = SubjectAllocationForm(request.POST)
        if form.is_valid():
            allocation = form.save(commit=False)
            allocation.class_assigned = class_obj
            allocation.save()
            messages.success(request, 'Subject allocated successfully.')
            return redirect('academics:subject_allocation_list', class_id=class_obj.id)
    else:
        form = SubjectAllocationForm()
        form.fields['subject'].queryset = Subject.objects.filter(is_active=True, classes__contains=[class_obj.class_level])
    
    return render(request, 'academics/subject_allocation_form.html', {
        'form': form,
        'class_obj': class_obj,
        'title': 'Allocate Subject'
    })

@login_required
@admin_required
def subject_allocation_delete(request, allocation_id):
    """Delete subject allocation"""
    allocation = get_object_or_404(SubjectAllocation, id=allocation_id)
    class_id = allocation.class_assigned.id
    
    if request.method == 'POST':
        allocation.delete()
        messages.success(request, 'Subject allocation removed successfully.')
    
    return redirect('academics:subject_allocation_list', class_id=class_id)

# ============== Exam Views ==============

@login_required
def exam_list(request):
    """List all exams"""
    exams = Exam.objects.all().select_related('term').order_by('-start_date')
    
    # Filter by term
    term_id = request.GET.get('term')
    if term_id:
        exams = exams.filter(term_id=term_id)
    
    terms = Term.objects.all().order_by('-academic_year', '-term')
    
    context = {
        'exams': exams,
        'terms': terms,
    }
    return render(request, 'academics/exam_list.html', context)

@login_required
@teacher_required
def exam_create(request):
    """Create new exam"""
    if request.method == 'POST':
        form = ExamForm(request.POST)
        if form.is_valid():
            exam = form.save(commit=False)
            exam.created_by = request.user
            exam.save()
            form.save_m2m()  # Save many-to-many subjects
            messages.success(request, f'Exam {exam.name} created successfully.')
            return redirect('academics:exam_detail', exam_id=exam.id)
    else:
        form = ExamForm()
    
    return render(request, 'academics/exam_form.html', {
        'form': form,
        'title': 'Create Exam'
    })

@login_required
def exam_detail(request, exam_id):
    """View exam details"""
    exam = get_object_or_404(Exam, id=exam_id)
    schedules = exam.schedule.all().select_related('subject', 'class_assigned').order_by('date', 'start_time')
    
    # Check if results have been entered
    results_count = Result.objects.filter(exam=exam).count()
    
    context = {
        'exam': exam,
        'schedules': schedules,
        'results_count': results_count,
    }
    return render(request, 'academics/exam_detail.html', context)

@login_required
@teacher_required
def exam_edit(request, exam_id):
    """Edit exam"""
    exam = get_object_or_404(Exam, id=exam_id)
    
    if request.method == 'POST':
        form = ExamForm(request.POST, instance=exam)
        if form.is_valid():
            form.save()
            messages.success(request, 'Exam updated successfully.')
            return redirect('academics:exam_detail', exam_id=exam.id)
    else:
        form = ExamForm(instance=exam)
    
    return render(request, 'academics/exam_form.html', {
        'form': form,
        'exam': exam,
        'title': 'Edit Exam'
    })

@login_required
@teacher_required
def exam_schedule_create(request, exam_id):
    """Create exam schedule"""
    exam = get_object_or_404(Exam, id=exam_id)
    
    if request.method == 'POST':
        form = ExamScheduleForm(request.POST)
        if form.is_valid():
            schedule = form.save(commit=False)
            schedule.exam = exam
            schedule.save()
            messages.success(request, 'Exam schedule added successfully.')
            return redirect('academics:exam_detail', exam_id=exam.id)
    else:
        form = ExamScheduleForm()
        form.fields['subject'].queryset = exam.subjects.all()
    
    return render(request, 'academics/exam_schedule_form.html', {
        'form': form,
        'exam': exam,
    })

@login_required
@teacher_required
def exam_publish(request, exam_id):
    """Publish exam results"""
    exam = get_object_or_404(Exam, id=exam_id)
    
    if request.method == 'POST':
        exam.is_published = True
        exam.save()
        messages.success(request, 'Exam results published successfully.')
    
    return redirect('academics:exam_detail', exam_id=exam.id)

# ============== Result Views ==============

@login_required
def result_list(request):
    """List results"""
    results = Result.objects.all().select_related('student', 'exam', 'subject').order_by('-exam__start_date')
    
    # Filter by exam
    exam_id = request.GET.get('exam')
    if exam_id:
        results = results.filter(exam_id=exam_id)
    
    # Filter by class
    class_level = request.GET.get('class')
    if class_level:
        results = results.filter(student__current_class=class_level)
    
    paginator = Paginator(results, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'exams': Exam.objects.all().order_by('-start_date'),
    }
    return render(request, 'academics/result_list.html', context)

@login_required
@teacher_required
def result_entry(request, exam_id, class_id=None):
    """Enter results for an exam"""
    exam = get_object_or_404(Exam, id=exam_id)
    
    # Get class if specified
    class_obj = None
    students = []
    class_mappings = {}  # Add this to store class ID mappings
    
    if class_id:
        class_obj = get_object_or_404(Class, id=class_id)
        students = Student.objects.filter(
            current_class=class_obj.class_level, 
            stream=class_obj.stream, 
            is_active=True
        ).order_by('user__first_name')
    else:
        # Get all classes for the current academic year
        from academics.models import Class, AcademicYear
        current_year = AcademicYear.objects.filter(is_current=True).first()
        if current_year:
            classes = Class.objects.filter(academic_year=current_year)
            # Create a mapping of "level_stream" to class_id
            for c in classes:
                key = f"{c.class_level}_{c.stream}"
                class_mappings[key] = c.id
        
        class_levels = [1, 2, 3, 4]
        streams = ['East', 'West', 'North', 'South']
    
    # Get subjects for this exam
    subjects = exam.subjects.all()
    
    # Get existing results
    existing_results = {}
    results = Result.objects.filter(exam=exam)
    for result in results:
        key = f"{result.student.id}_{result.subject.id}"
        existing_results[key] = result
    
    context = {
        'exam': exam,
        'class_obj': class_obj,
        'students': students,
        'subjects': subjects,
        'existing_results': existing_results,
        'class_levels': class_levels if not class_obj else None,
        'streams': streams if not class_obj else None,
        'class_mappings': class_mappings,  # Add this to context
    }
    
    return render(request, 'academics/result_entry.html', context)

@login_required
@teacher_required
def result_bulk_upload(request, exam_id):
    """Bulk upload results via CSV"""
    exam = get_object_or_404(Exam, id=exam_id)
    
    if request.method == 'POST':
        form = ResultBulkUploadForm(request.POST, request.FILES)
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
                    student = Student.objects.get(admission_number=row['admission_number'])
                    subject = Subject.objects.get(code=row['subject_code'])
                    
                    result, created = Result.objects.update_or_create(
                        student=student,
                        exam=exam,
                        subject=subject,
                        defaults={
                            'marks': int(row['marks']),
                            'entered_by': request.user,
                        }
                    )
                    success_count += 1
                    
                except Exception as e:
                    error_count += 1
                    errors.append(f"Row {success_count + error_count}: {str(e)}")
            
            messages.success(request, f'Successfully imported {success_count} results. {error_count} errors.')
            if errors:
                request.session['import_errors'] = errors
            
            return redirect('academics:exam_detail', exam_id=exam.id)
    else:
        form = ResultBulkUploadForm()
    
    return render(request, 'academics/result_bulk_upload.html', {
        'form': form,
        'exam': exam,
    })

@login_required
def student_results(request, student_id):
    """View results for a specific student"""
    student = get_object_or_404(Student, id=student_id)
    
    # Check permission
    if not (request.user.is_admin() or request.user.is_teacher() or request.user == student.user):
        messages.error(request, 'You do not have permission to view this page.')
        return redirect('dashboard:home')
    
    # Get results grouped by term
    results = Result.objects.filter(student=student).select_related('exam__term', 'subject').order_by('-exam__start_date')
    
    # Group by term
    terms = {}
    for result in results:
        term_key = str(result.exam.term)
        if term_key not in terms:
            terms[term_key] = {
                'term': result.exam.term,
                'results': [],
                'total': 0,
                'count': 0
            }
        terms[term_key]['results'].append(result)
        terms[term_key]['total'] += result.marks
        terms[term_key]['count'] += 1
    
    # Get summaries
    summaries = ResultSummary.objects.filter(student=student).select_related('term')
    summary_dict = {str(s.term): s for s in summaries}
    
    context = {
        'student': student,
        'terms': terms,
        'summaries': summary_dict,
    }
    
    return render(request, 'academics/student_results.html', context)

@login_required
def class_results(request, class_id, term_id=None):
    """View results for a whole class"""
    class_obj = get_object_or_404(Class, id=class_id)
    
    # Get term
    if term_id:
        term = get_object_or_404(Term, id=term_id)
    else:
        term = Term.objects.filter(academic_year=class_obj.academic_year, is_current=True).first()
    
    if not term:
        messages.error(request, 'No term selected.')
        return redirect('academics:class_list')
    
    # Get students in this class
    students = Student.objects.filter(
        current_class=class_obj.class_level,
        stream=class_obj.stream,
        is_active=True
    ).order_by('user__first_name')
    
    # Get results for this term
    results = Result.objects.filter(
        student__in=students,
        exam__term=term
    ).select_related('student', 'subject')
    
    # Get summaries
    summaries = ResultSummary.objects.filter(
        student__in=students,
        term=term
    ).select_related('student')
    
    # Organize data
    results_data = {}
    for student in students:
        results_data[student.id] = {
            'student': student,
            'results': {},
            'summary': None
        }
    
    for result in results:
        results_data[result.student.id]['results'][result.subject.id] = result
    
    for summary in summaries:
        if summary.student.id in results_data:
            results_data[summary.student.id]['summary'] = summary
    
    context = {
        'class_obj': class_obj,
        'term': term,
        'results_data': results_data,
        'terms': Term.objects.filter(academic_year=class_obj.academic_year),
    }
    
    return render(request, 'academics/class_results.html', context)

# ============== Ranking Views ==============

@login_required
def ranking_dashboard(request):
    """Ranking dashboard"""
    current_term = Term.objects.filter(is_current=True).first()
    
    if not current_term:
        messages.error(request, 'No current term set.')
        return redirect('academics:term_list')
    
    # Get top performers overall
    top_overall = RankingService.get_top_performers(current_term, limit=10)
    
    # Get top performers per class
    top_per_class = {}
    for class_level in range(1, 5):
        top_per_class[class_level] = RankingService.get_top_performers(
            current_term, class_level=class_level, limit=5
        )
    
    # Get class mean scores
    class_means = {}
    for class_level in range(1, 5):
        class_means[class_level] = RankingService.get_class_mean_score(current_term, class_level)
    
    context = {
        'current_term': current_term,
        'top_overall': top_overall,
        'top_per_class': top_per_class,
        'class_means': class_means,
    }
    
    return render(request, 'academics/ranking_dashboard.html', context)

@login_required
def class_ranking(request, class_level, term_id=None):
    """View ranking for a specific class level"""
    # Get term
    if term_id:
        term = get_object_or_404(Term, id=term_id)
    else:
        term = Term.objects.filter(is_current=True).first()
    
    if not term:
        messages.error(request, 'No term selected.')
        return redirect('academics:ranking_dashboard')
    
    # Get all streams in this class level
    streams = ['East', 'West', 'North', 'South']
    
    stream_data = {}
    for stream in streams:
        students = Student.objects.filter(
            current_class=class_level,
            stream=stream,
            is_active=True
        )
        
        summaries = ResultSummary.objects.filter(
            student__in=students,
            term=term
        ).select_related('student').order_by('-average')
        
        stream_data[stream] = summaries
    
    context = {
        'class_level': class_level,
        'term': term,
        'stream_data': stream_data,
        'terms': Term.objects.all().order_by('-academic_year', '-term'),
    }
    
    return render(request, 'academics/class_ranking.html', context)

@login_required
def update_rankings(request, term_id):
    """Manually trigger ranking update"""
    if not request.user.is_admin():
        messages.error(request, 'Permission denied.')
        return redirect('academics:ranking_dashboard')
    
    term = get_object_or_404(Term, id=term_id)
    
    # Update all summaries and rankings
    RankingService.update_term_summaries(term)
    RankingService.calculate_overall_positions(term)
    
    messages.success(request, f'Rankings updated for {term}.')
    return redirect('academics:ranking_dashboard')

# ============== Performance Analysis Views ==============

@login_required
def performance_analysis(request):
    """Performance analysis dashboard"""
    current_term = Term.objects.filter(is_current=True).first()
    
    if not current_term:
        messages.error(request, 'No current term set.')
        return redirect('academics:term_list')
    
    # Analyze overall school performance
    school_analysis = {}
    for class_level in range(1, 5):
        school_analysis[class_level] = PerformanceAnalyzer.analyze_class_performance(
            current_term, class_level
        )
    
    # Compare streams
    stream_comparison = {}
    for class_level in range(1, 5):
        stream_comparison[class_level] = PerformanceAnalyzer.compare_streams(
            current_term, class_level
        )
    
    # Subject analysis
    subject_analysis = PerformanceAnalyzer.subject_performance_analysis(current_term)
    
    context = {
        'current_term': current_term,
        'school_analysis': school_analysis,
        'stream_comparison': stream_comparison,
        'subject_analysis': subject_analysis,
    }
    
    return render(request, 'academics/performance_analysis.html', context)

# ============== Homework Views ==============

@login_required
def homework_list(request):
    """List homework assignments"""
    
    # Base queryset
    homeworks = Homework.objects.all().select_related(
        'subject', 'teacher', 'class_assigned'
    )
    
    # Filter based on user role
    if request.user.role == 'teacher':
        # Teachers see homework they created
        try:
            teacher = request.user.teacher_profile
            homeworks = homeworks.filter(teacher=teacher)
        except Teacher.DoesNotExist:
            # Teacher profile doesn't exist, show empty queryset
            homeworks = Homework.objects.none()
            messages.warning(request, 'Your teacher profile is not fully set up. Please contact administrator.')
    
    elif request.user.role == 'student':
        # Students see homework for their class
        try:
            student = request.user.student_profile
            homeworks = homeworks.filter(
                class_assigned__class_level=student.current_class,
                class_assigned__stream=student.stream
            )
        except Student.DoesNotExist:
            # Student profile doesn't exist, show empty queryset
            homeworks = Homework.objects.none()
            messages.warning(request, 'Your student profile is not fully set up. Please contact administrator.')
    
    # Admin and other roles see all homework
    # No additional filtering needed
    
    # Order by due date
    homeworks = homeworks.order_by('-due_date')
    
    # Get statistics
    total_homeworks = homeworks.count()
    today = timezone.now().date()
    
    active_count = homeworks.filter(
        due_date__gte=today,
        is_submitted=False
    ).count()
    
    overdue_count = homeworks.filter(
        due_date__lt=today,
        is_submitted=False
    ).count()
    
    # Calculate completion rate (for teachers/admin)
    completion_rate = 0
    if homeworks.exists() and (request.user.role in ['admin', 'teacher']):
        # Get total submissions
        total_submissions = HomeworkSubmission.objects.filter(
            homework__in=homeworks
        ).count()
        
        # Calculate expected submissions properly WITHOUT using 'students_count' field
        expected_submissions = 0
        from students.models import Student
        
        # Iterate through each homework and count students in the target class
        for homework in homeworks:
            student_count = Student.objects.filter(
                current_class=homework.class_assigned.class_level,
                stream=homework.class_assigned.stream,
                is_active=True
            ).count()
            expected_submissions += student_count
        
        completion_rate = (total_submissions / expected_submissions * 100) if expected_submissions > 0 else 0
    
    # Get subjects and classes for filters
    subjects = Subject.objects.filter(is_active=True)
    classes = Class.objects.filter(academic_year__is_current=True)
    
    # Apply filters from request
    if request.GET.get('subject'):
        homeworks = homeworks.filter(subject_id=request.GET.get('subject'))
    if request.GET.get('class'):
        homeworks = homeworks.filter(class_assigned_id=request.GET.get('class'))
    
    # Status filter
    status = request.GET.get('status')
    if status == 'active':
        homeworks = homeworks.filter(due_date__gte=today, is_submitted=False)
    elif status == 'overdue':
        homeworks = homeworks.filter(due_date__lt=today, is_submitted=False)
    elif status == 'completed':
        homeworks = homeworks.filter(is_submitted=True)
    
    # Pagination
    paginator = Paginator(homeworks, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'homeworks': page_obj,
        'total_homeworks': total_homeworks,
        'active_count': active_count,
        'overdue_count': overdue_count,
        'completion_rate': completion_rate,
        'subjects': subjects,
        'classes': classes,
        'today': today,
    }
    
    return render(request, 'academics/homework_list.html', context)

    
@login_required
@teacher_required
def download_result_template(request, exam_id):
    """Download CSV template for bulk upload"""
    import csv
    from django.http import HttpResponse
    
    exam = get_object_or_404(Exam, id=exam_id)
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="results_template_{exam.id}.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['admission_number', 'subject_code', 'marks', 'remarks'])
    
    # Add sample rows
    writer.writerow(['ADM/2024/1001', 'MAT', '', ''])
    writer.writerow(['ADM/2024/1001', 'ENG', '', ''])
    writer.writerow(['ADM/2024/1002', 'MAT', '', ''])
    
    return response

@login_required
@teacher_required
def homework_create(request):
    """Create homework assignment"""
    if request.method == 'POST':
        form = HomeworkForm(request.POST, request.FILES)
        if form.is_valid():
            homework = form.save(commit=False)
            homework.teacher = request.user.teacher_profile
            homework.save()
            messages.success(request, 'Homework assigned successfully.')
            return redirect('academics:homework_list')
    else:
        form = HomeworkForm()
    
    return render(request, 'academics/homework_form.html', {
        'form': form,
        'title': 'Assign Homework'
    })

@login_required
def homework_detail(request, homework_id):
    """View homework details"""
    homework = get_object_or_404(Homework, id=homework_id)
    
    # Check permission
    if request.user.is_student():
        student = request.user.student_profile
        submission = HomeworkSubmission.objects.filter(homework=homework, student=student).first()
    else:
        submission = None
        submissions = homework.submissions.all().select_related('student')
    
    context = {
        'homework': homework,
        'submission': submission,
        'submissions': submissions if request.user.is_teacher() else None,
    }
    
    return render(request, 'academics/homework_detail.html', context)



@login_required
@teacher_required
def homework_edit(request, homework_id):
    """Edit homework"""
    homework = get_object_or_404(Homework, id=homework_id)
    
    if request.method == 'POST':
        form = HomeworkForm(request.POST, request.FILES, instance=homework)
        if form.is_valid():
            form.save()
            messages.success(request, 'Homework updated successfully.')
            return redirect('academics:homework_detail', homework_id=homework.id)
    else:
        form = HomeworkForm(instance=homework)
    
    return render(request, 'academics/homework_form.html', {
        'form': form,
        'homework': homework,
        'title': 'Edit Homework'
    })

@login_required
def homework_submit(request, homework_id):
    """Submit homework as student"""
    homework = get_object_or_404(Homework, id=homework_id)
    
    if not request.user.is_student():
        messages.error(request, 'Only students can submit homework.')
        return redirect('academics:homework_detail', homework_id=homework.id)
    
    student = request.user.student_profile
    
    # Check if already submitted
    if HomeworkSubmission.objects.filter(homework=homework, student=student).exists():
        messages.error(request, 'You have already submitted this homework.')
        return redirect('academics:homework_detail', homework_id=homework.id)
    
    if request.method == 'POST':
        form = HomeworkSubmissionForm(request.POST, request.FILES)
        if form.is_valid():
            submission = form.save(commit=False)
            submission.homework = homework
            submission.student = student
            submission.save()
            messages.success(request, 'Homework submitted successfully.')
            return redirect('academics:homework_detail', homework_id=homework.id)
    else:
        form = HomeworkSubmissionForm()
    
    return render(request, 'academics/homework_submit.html', {
        'form': form,
        'homework': homework,
    })

@login_required
@teacher_required
def homework_grade(request, submission_id):
    """Grade homework submission"""
    submission = get_object_or_404(HomeworkSubmission, id=submission_id)
    
    if request.method == 'POST':
        marks = request.POST.get('marks')
        feedback = request.POST.get('feedback')
        
        submission.marks = marks
        submission.feedback = feedback
        submission.graded_by = request.user
        submission.graded_at = timezone.now()
        submission.save()
        
        messages.success(request, 'Homework graded successfully.')
    
    return redirect('academics:homework_detail', homework_id=submission.homework.id)

# ============== API Views ==============

@login_required
def get_subjects_for_class(request, class_level):
    """API endpoint to get subjects for a class level"""
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        subjects = Subject.objects.filter(is_active=True, classes__contains=[class_level])
        data = [{'id': s.id, 'name': s.name, 'code': s.code} for s in subjects]
        return JsonResponse(data, safe=False)
    return JsonResponse({'error': 'Invalid request'}, status=400)

@login_required
def get_teachers_for_subject(request, subject_id):
    """API endpoint to get teachers for a subject"""
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        from teachers.models import TeacherSubject
        teacher_subjects = TeacherSubject.objects.filter(subject_id=subject_id).select_related('teacher')
        data = [{'id': ts.teacher.id, 'name': ts.teacher.get_full_name()} for ts in teacher_subjects]
        return JsonResponse(data, safe=False)
    return JsonResponse({'error': 'Invalid request'}, status=400)


@login_required
def export_results(request):
    """Export results to CSV"""
    import csv
    from django.http import HttpResponse
    from django.db.models import Q
    
    # Get filters from request
    exam_id = request.GET.get('exam')
    class_level = request.GET.get('class')
    subject_id = request.GET.get('subject')
    
    # Base queryset
    results = Result.objects.all().select_related(
        'student', 'exam', 'subject', 'student__user'
    )
    
    # Apply filters
    if exam_id:
        results = results.filter(exam_id=exam_id)
    if class_level:
        results = results.filter(student__current_class=class_level)
    if subject_id:
        results = results.filter(subject_id=subject_id)
    
    # Create CSV response
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="results_export.csv"'
    
    writer = csv.writer(response)
    writer.writerow([
        'Student Name', 'Admission No.', 'Class', 'Exam', 'Subject',
        'Marks', 'Grade', 'Points', 'Remarks'
    ])
    
    for result in results:
        writer.writerow([
            result.student.get_full_name(),
            result.student.admission_number,
            f"Form {result.student.current_class} {result.student.stream}",
            result.exam.name,
            result.subject.name,
            result.marks,
            result.grade,
            result.points,
            result.remarks
        ])
    
    return response