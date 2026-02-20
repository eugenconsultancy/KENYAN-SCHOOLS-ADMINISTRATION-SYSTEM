from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse, FileResponse
from django.utils import timezone
from accounts.decorators import role_required
from .report_generator import ReportGenerator
from .attendance_reports import AttendanceReportGenerator
from .result_reports import ResultReportGenerator
from .finance_reports import FinanceReportGenerator
from students.models import Student
from teachers.models import Teacher
from academics.models import Term, Exam, Class
import os

@login_required
def report_index(request):
    """Reports dashboard"""
    
    recent_reports = ReportGenerator.get_recent_reports(request.user)
    
    context = {
        'recent_reports': recent_reports,
    }
    
    return render(request, 'reports/index.html', context)

# ============== Student Reports ==============

@login_required
def student_report(request, student_id):
    """Generate individual student report"""
    
    student = get_object_or_404(Student, id=student_id)
    
    # Check permission
    if not (request.user.is_admin() or request.user.is_teacher() or request.user == student.user):
        messages.error(request, 'You do not have permission to view this report.')
        return redirect('dashboard:home')
    
    term_id = request.GET.get('term')
    
    if term_id:
        term = get_object_or_404(Term, id=term_id)
        pdf_path = ResultReportGenerator.generate_student_term_report(student, term)
    else:
        # Generate comprehensive student profile
        pdf_path = ReportGenerator.generate_student_profile(student)
    
    if pdf_path and os.path.exists(pdf_path):
        return FileResponse(open(pdf_path, 'rb'), content_type='application/pdf', filename=os.path.basename(pdf_path))
    else:
        messages.error(request, 'Error generating report.')
        return redirect('students:detail', student_id=student.id)

@login_required
def student_list_report(request):
    """Generate student list report"""
    
    class_level = request.GET.get('class_level')
    stream = request.GET.get('stream')
    
    students = Student.objects.filter(is_active=True)
    
    if class_level:
        students = students.filter(current_class=class_level)
    if stream:
        students = students.filter(stream=stream)
    
    students = students.order_by('current_class', 'stream', 'user__first_name')
    
    pdf_path = ReportGenerator.generate_student_list(students, class_level, stream)
    
    if pdf_path and os.path.exists(pdf_path):
        return FileResponse(open(pdf_path, 'rb'), content_type='application/pdf', filename=os.path.basename(pdf_path))
    else:
        messages.error(request, 'Error generating report.')
        return redirect('reports:index')

# ============== Academic Reports ==============

@login_required
def class_result_slip(request, class_id, exam_id):
    """Generate result slips for an entire class"""
    
    class_obj = get_object_or_404(Class, id=class_id)
    exam = get_object_or_404(Exam, id=exam_id)
    
    pdf_path = ResultReportGenerator.generate_class_result_slips(class_obj, exam)
    
    if pdf_path and os.path.exists(pdf_path):
        return FileResponse(open(pdf_path, 'rb'), content_type='application/pdf', filename=f"results_{class_obj}_{exam}.pdf")
    else:
        messages.error(request, 'Error generating result slips.')
        return redirect('academics:class_results', class_id=class_obj.id)

@login_required
def term_report(request, term_id):
    """Generate comprehensive term report"""
    
    term = get_object_or_404(Term, id=term_id)
    
    class_level = request.GET.get('class_level')
    stream = request.GET.get('stream')
    
    pdf_path = ResultReportGenerator.generate_term_report(term, class_level, stream)
    
    if pdf_path and os.path.exists(pdf_path):
        filename = f"term_report_{term.academic_year}_{term.term}"
        if class_level:
            filename += f"_form_{class_level}"
        if stream:
            filename += f"_{stream}"
        return FileResponse(open(pdf_path, 'rb'), content_type='application/pdf', filename=f"{filename}.pdf")
    else:
        messages.error(request, 'Error generating term report.')
        return redirect('reports:index')

@login_required
def exam_performance_report(request, exam_id):
    """Generate exam performance analysis report"""
    
    exam = get_object_or_404(Exam, id=exam_id)
    
    pdf_path = ResultReportGenerator.generate_exam_performance_report(exam)
    
    if pdf_path and os.path.exists(pdf_path):
        return FileResponse(open(pdf_path, 'rb'), content_type='application/pdf', filename=f"exam_performance_{exam.name}.pdf")
    else:
        messages.error(request, 'Error generating exam report.')
        return redirect('academics:exam_detail', exam_id=exam.id)

@login_required
def ranking_report(request, term_id):
    """Generate ranking report"""
    
    term = get_object_or_404(Term, id=term_id)
    
    class_level = request.GET.get('class_level')
    
    pdf_path = ResultReportGenerator.generate_ranking_report(term, class_level)
    
    if pdf_path and os.path.exists(pdf_path):
        filename = f"rankings_{term.academic_year}_{term.term}"
        if class_level:
            filename += f"_form_{class_level}"
        return FileResponse(open(pdf_path, 'rb'), content_type='application/pdf', filename=f"{filename}.pdf")
    else:
        messages.error(request, 'Error generating ranking report.')
        return redirect('reports:index')

# ============== Attendance Reports ==============

@login_required
def attendance_report(request):
    """Generate attendance report"""
    
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    class_level = request.GET.get('class_level')
    stream = request.GET.get('stream')
    
    if not start_date or not end_date:
        messages.error(request, 'Please select date range.')
        return redirect('reports:index')
    
    pdf_path = AttendanceReportGenerator.generate_attendance_report(
        start_date, end_date, class_level, stream
    )
    
    if pdf_path and os.path.exists(pdf_path):
        filename = f"attendance_report_{start_date}_to_{end_date}.pdf"
        return FileResponse(open(pdf_path, 'rb'), content_type='application/pdf', filename=filename)
    else:
        messages.error(request, 'Error generating attendance report.')
        return redirect('reports:index')

@login_required
def student_attendance_report(request, student_id):
    """Generate individual student attendance report"""
    
    student = get_object_or_404(Student, id=student_id)
    
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    pdf_path = AttendanceReportGenerator.generate_student_attendance_report(
        student, start_date, end_date
    )
    
    if pdf_path and os.path.exists(pdf_path):
        filename = f"attendance_{student.admission_number}.pdf"
        return FileResponse(open(pdf_path, 'rb'), content_type='application/pdf', filename=filename)
    else:
        messages.error(request, 'Error generating attendance report.')
        return redirect('attendance:student_attendance', student_id=student.id)

@login_required
def monthly_attendance_summary(request, year, month):
    """Generate monthly attendance summary"""
    
    class_level = request.GET.get('class_level')
    
    pdf_path = AttendanceReportGenerator.generate_monthly_summary(year, month, class_level)
    
    if pdf_path and os.path.exists(pdf_path):
        filename = f"attendance_summary_{year}_{month}.pdf"
        return FileResponse(open(pdf_path, 'rb'), content_type='application/pdf', filename=filename)
    else:
        messages.error(request, 'Error generating attendance summary.')
        return redirect('reports:index')

# ============== Finance Reports ==============

@login_required
def fee_statement(request, student_id):
    """Generate fee statement for a student"""
    
    student = get_object_or_404(Student, id=student_id)
    
    pdf_path = FinanceReportGenerator.generate_fee_statement(student)
    
    if pdf_path and os.path.exists(pdf_path):
        filename = f"fee_statement_{student.admission_number}.pdf"
        return FileResponse(open(pdf_path, 'rb'), content_type='application/pdf', filename=filename)
    else:
        messages.error(request, 'Error generating fee statement.')
        return redirect('finance:student_invoices', student_id=student.id)

@login_required
def collection_report(request):
    """Generate collection report"""
    
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    if not start_date or not end_date:
        messages.error(request, 'Please select date range.')
        return redirect('reports:index')
    
    pdf_path = FinanceReportGenerator.generate_collection_report(start_date, end_date)
    
    if pdf_path and os.path.exists(pdf_path):
        filename = f"collection_report_{start_date}_to_{end_date}.pdf"
        return FileResponse(open(pdf_path, 'rb'), content_type='application/pdf', filename=filename)
    else:
        messages.error(request, 'Error generating collection report.')
        return redirect('reports:index')

@login_required
def outstanding_report(request):
    """Generate outstanding fees report"""
    
    as_at = request.GET.get('as_at', timezone.now().date().isoformat())
    
    pdf_path = FinanceReportGenerator.generate_outstanding_report(as_at)
    
    if pdf_path and os.path.exists(pdf_path):
        filename = f"outstanding_report_{as_at}.pdf"
        return FileResponse(open(pdf_path, 'rb'), content_type='application/pdf', filename=filename)
    else:
        messages.error(request, 'Error generating outstanding report.')
        return redirect('reports:index')

@login_required
def budget_report(request, year):
    """Generate budget vs actual report"""
    
    pdf_path = FinanceReportGenerator.generate_budget_report(year)
    
    if pdf_path and os.path.exists(pdf_path):
        filename = f"budget_report_{year}.pdf"
        return FileResponse(open(pdf_path, 'rb'), content_type='application/pdf', filename=filename)
    else:
        messages.error(request, 'Error generating budget report.')
        return redirect('reports:index')

# ============== Teacher Reports ==============

@login_required
def teacher_report(request, teacher_id):
    """Generate teacher report"""
    
    teacher = get_object_or_404(Teacher, id=teacher_id)
    
    pdf_path = ReportGenerator.generate_teacher_profile(teacher)
    
    if pdf_path and os.path.exists(pdf_path):
        filename = f"teacher_{teacher.employee_number}.pdf"
        return FileResponse(open(pdf_path, 'rb'), content_type='application/pdf', filename=filename)
    else:
        messages.error(request, 'Error generating teacher report.')
        return redirect('teachers:detail', teacher_id=teacher.id)

@login_required
def teacher_list_report(request):
    """Generate teacher list report"""
    
    teachers = Teacher.objects.filter(is_active=True).order_by('user__first_name')
    
    pdf_path = ReportGenerator.generate_teacher_list(teachers)
    
    if pdf_path and os.path.exists(pdf_path):
        filename = "teacher_list.pdf"
        return FileResponse(open(pdf_path, 'rb'), content_type='application/pdf', filename=filename)
    else:
        messages.error(request, 'Error generating teacher list.')
        return redirect('reports:index')

# ============== Custom Reports ==============

@login_required
def custom_report(request):
    """Generate custom report based on selected criteria"""
    
    if request.method == 'POST':
        report_type = request.POST.get('report_type')
        include_charts = request.POST.get('include_charts') == 'on'
        include_tables = request.POST.get('include_tables') == 'on'
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        
        # Get selected sections
        sections = []
        if request.POST.get('section_students'):
            sections.append('students')
        if request.POST.get('section_teachers'):
            sections.append('teachers')
        if request.POST.get('section_academics'):
            sections.append('academics')
        if request.POST.get('section_finance'):
            sections.append('finance')
        if request.POST.get('section_attendance'):
            sections.append('attendance')
        
        pdf_path = ReportGenerator.generate_custom_report(
            sections=sections,
            start_date=start_date,
            end_date=end_date,
            include_charts=include_charts,
            include_tables=include_tables
        )
        
        if pdf_path and os.path.exists(pdf_path):
            filename = f"custom_report_{timezone.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            return FileResponse(open(pdf_path, 'rb'), content_type='application/pdf', filename=filename)
        else:
            messages.error(request, 'Error generating custom report.')
    
    return render(request, 'reports/custom_report_form.html')