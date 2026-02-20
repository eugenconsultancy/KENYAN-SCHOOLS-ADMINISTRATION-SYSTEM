from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Count, Sum, Avg
from django.core.paginator import Paginator
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from accounts.decorators import role_required, teacher_required, admin_required
from .models import (
    Attendance, TeacherAttendance, AttendanceSession, DailyAttendanceRegister,
    Holiday, AttendanceReport, AttendanceNotification
)
from .forms import (
    AttendanceForm, BulkAttendanceForm, TeacherAttendanceForm,
    DateRangeForm, HolidayForm, AttendanceReportForm,
    AttendanceFilterForm, AttendanceSessionForm, AttendanceNotificationForm
)
from .services import AttendanceService, ReportService, NotificationService
from students.models import Student
from teachers.models import Teacher
from academics.models import Class, Term
import csv
import json

# ============== Dashboard Views ==============

@login_required
def attendance_dashboard(request):
    """Main attendance dashboard"""
    
    today = timezone.now().date()
    
    # Today's statistics
    today_total = Attendance.objects.filter(date=today).count()
    today_present = Attendance.objects.filter(date=today, status='present').count()
    today_absent = Attendance.objects.filter(date=today, status='absent').count()
    today_late = Attendance.objects.filter(date=today, status='late').count()
    
    # Overall statistics for current term
    current_term = Term.objects.filter(is_current=True).first()
    if current_term:
        term_attendance = Attendance.objects.filter(
            date__gte=current_term.start_date,
            date__lte=current_term.end_date
        )
        term_total = term_attendance.count()
        term_present = term_attendance.filter(status='present').count()
        term_percentage = (term_present / term_total * 100) if term_total > 0 else 0
    else:
        term_percentage = 0
    
    # Class-wise attendance today
    class_attendance = []
    for class_level in range(1, 5):
        for stream in ['East', 'West', 'North', 'South']:
            count = Attendance.objects.filter(
                date=today,
                class_level=class_level,
                stream=stream
            ).count()
            if count > 0:
                present = Attendance.objects.filter(
                    date=today,
                    class_level=class_level,
                    stream=stream,
                    status='present'
                ).count()
                percentage = (present / count * 100) if count > 0 else 0
                
                class_attendance.append({
                    'class': f"Form {class_level} {stream}",
                    'total': count,
                    'present': present,
                    'percentage': round(percentage, 1)
                })
    
    # Recent attendance records
    recent = Attendance.objects.select_related('student').order_by('-date', '-marked_at')[:20]
    
    context = {
        'today_total': today_total,
        'today_present': today_present,
        'today_absent': today_absent,
        'today_late': today_late,
        'today_attendance_rate': (today_present / today_total * 100) if today_total > 0 else 0,
        'term_percentage': round(term_percentage, 1),
        'class_attendance': class_attendance,
        'recent': recent,
    }
    
    return render(request, 'attendance/dashboard.html', context)

# ============== Student Attendance Views ==============

@login_required
def mark_attendance(request):
    """Mark attendance for a class"""
    
    if request.method == 'POST':
        form = BulkAttendanceForm(request.POST)
        if form.is_valid():
            date = form.cleaned_data['date']
            session = form.cleaned_data['session']
            class_level = form.cleaned_data['class_level']
            stream = form.cleaned_data['stream']
            
            # Get students in this class
            students = Student.objects.filter(
                current_class=class_level,
                stream=stream,
                is_active=True
            ).order_by('user__first_name')
            
            # Get or create register
            class_obj = Class.objects.filter(
                class_level=class_level,
                stream=stream,
                academic_year__is_current=True
            ).first()
            
            if class_obj:
                register, created = DailyAttendanceRegister.objects.get_or_create(
                    class_assigned=class_obj,
                    date=date,
                    session=session,
                    defaults={'created_by': request.user}
                )
            
            # Process attendance
            for student in students:
                status = request.POST.get(f"status_{student.id}", 'absent')
                reason = request.POST.get(f"reason_{student.id}", '')
                
                attendance, created = Attendance.objects.update_or_create(
                    student=student,
                    date=date,
                    session=session,
                    defaults={
                        'status': status,
                        'reason': reason,
                        'marked_by': request.user,
                        'class_level': class_level,
                        'stream': stream,
                    }
                )
            
            # Update register statistics
            if class_obj:
                register.update_statistics()
            
            messages.success(request, f'Attendance marked for Form {class_level} {stream} on {date}')
            return redirect('attendance:class_attendance', class_level=class_level, stream=stream)
    else:
        form = BulkAttendanceForm()
    
    return render(request, 'attendance/mark_attendance.html', {'form': form})

@login_required
def class_attendance(request, class_level, stream):
    """View attendance for a specific class"""
    
    date = request.GET.get('date', timezone.now().date().isoformat())
    
    # Get students
    students = Student.objects.filter(
        current_class=class_level,
        stream=stream,
        is_active=True
    ).order_by('user__first_name')
    
    # Get attendance for this date
    attendance_records = {}
    for student in students:
        try:
            attendance = Attendance.objects.get(
                student=student,
                date=date
            )
            attendance_records[student.id] = attendance
        except Attendance.DoesNotExist:
            attendance_records[student.id] = None
    
    # Get attendance summary for this class
    summary = AttendanceService.get_class_attendance_summary(class_level, stream, date)
    
    context = {
        'class_level': class_level,
        'stream': stream,
        'date': date,
        'students': students,
        'attendance_records': attendance_records,
        'summary': summary,
    }
    
    return render(request, 'attendance/class_attendance.html', context)

@login_required
def student_attendance(request, student_id):
    """View attendance for a specific student"""
    
    student = get_object_or_404(Student, id=student_id)
    
    # Check permission
    if not (request.user.is_admin() or request.user.is_teacher() or request.user == student.user):
        messages.error(request, 'You do not have permission to view this page.')
        return redirect('dashboard:home')
    
    # Get date range
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    attendance = Attendance.objects.filter(student=student).order_by('-date')
    
    if start_date:
        attendance = attendance.filter(date__gte=start_date)
    if end_date:
        attendance = attendance.filter(date__lte=end_date)
    
    # Get monthly summaries
    summaries = student.attendance_summaries.all().order_by('-year', '-month')[:12]
    
    # Calculate statistics
    total_days = attendance.count()
    present_days = attendance.filter(status='present').count()
    absent_days = attendance.filter(status='absent').count()
    late_days = attendance.filter(status='late').count()
    excused_days = attendance.filter(status__in=['excused', 'sick']).count()
    
    context = {
        'student': student,
        'attendance': attendance,
        'summaries': summaries,
        'total_days': total_days,
        'present_days': present_days,
        'absent_days': absent_days,
        'late_days': late_days,
        'excused_days': excused_days,
        'attendance_percentage': (present_days / total_days * 100) if total_days > 0 else 0,
    }
    
    return render(request, 'attendance/student_attendance.html', context)

@login_required
@teacher_required
def edit_attendance(request, attendance_id):
    """Edit attendance record"""
    
    attendance = get_object_or_404(Attendance, id=attendance_id)
    
    if request.method == 'POST':
        form = AttendanceForm(request.POST, instance=attendance)
        if form.is_valid():
            form.save()
            messages.success(request, 'Attendance record updated.')
            return redirect('attendance:student_attendance', student_id=attendance.student.id)
    else:
        form = AttendanceForm(instance=attendance)
    
    return render(request, 'attendance/attendance_form.html', {
        'form': form,
        'attendance': attendance
    })

# ============== Teacher Attendance Views ==============

@login_required
def teacher_attendance_mark(request):
    """Mark teacher attendance"""
    
    if request.method == 'POST':
        form = TeacherAttendanceForm(request.POST)
        if form.is_valid():
            attendance = form.save(commit=False)
            attendance.marked_by = request.user
            attendance.save()
            messages.success(request, 'Teacher attendance marked.')
            return redirect('attendance:teacher_attendance_list')
    else:
        form = TeacherAttendanceForm()
        # If teacher is logged in, pre-select them
        if request.user.is_teacher():
            try:
                teacher = request.user.teacher_profile
                form.fields['teacher'].initial = teacher
            except:
                pass
    
    return render(request, 'attendance/teacher_attendance_form.html', {'form': form})

@login_required
def teacher_attendance_list(request):
    """List teacher attendance"""
    
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
        'is_admin': request.user.is_admin(),
    }
    
    return render(request, 'attendance/teacher_attendance_list.html', context)

# ============== Report Views ==============

@login_required
def attendance_reports(request):
    """Attendance reports dashboard"""
    
    recent_reports = AttendanceReport.objects.all().order_by('-generated_at')[:10]
    
    context = {
        'recent_reports': recent_reports,
    }
    
    return render(request, 'attendance/reports.html', context)

@login_required
def generate_report(request):
    """Generate attendance report"""
    
    if request.method == 'POST':
        form = AttendanceReportForm(request.POST)
        if form.is_valid():
            report = form.save(commit=False)
            report.generated_by = request.user
            
            # Generate report file
            file_path = ReportService.generate_attendance_report(
                report_type=report.report_type,
                start_date=report.start_date,
                end_date=report.end_date,
                class_level=report.class_level,
                stream=report.stream
            )
            
            if file_path:
                report.report_file = file_path
                report.save()
                messages.success(request, 'Report generated successfully.')
                return redirect('attendance:download_report', report_id=report.id)
            else:
                messages.error(request, 'Error generating report.')
    else:
        form = AttendanceReportForm()
    
    return render(request, 'attendance/generate_report.html', {'form': form})

@login_required
def download_report(request, report_id):
    """Download generated report"""
    
    report = get_object_or_404(AttendanceReport, id=report_id)
    
    if report.report_file:
        response = HttpResponse(report.report_file.read(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{report.title}.pdf"'
        return response
    
    messages.error(request, 'Report file not found.')
    return redirect('attendance:attendance_reports')

@login_required
def export_attendance_csv(request):
    """Export attendance data to CSV"""
    
    # Get filters
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    class_level = request.GET.get('class_level')
    stream = request.GET.get('stream')
    
    attendance = Attendance.objects.select_related('student').all()
    
    if start_date:
        attendance = attendance.filter(date__gte=start_date)
    if end_date:
        attendance = attendance.filter(date__lte=end_date)
    if class_level:
        attendance = attendance.filter(class_level=class_level)
    if stream:
        attendance = attendance.filter(stream=stream)
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="attendance_export.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Date', 'Student Name', 'Admission No', 'Class', 'Stream', 'Status', 'Reason'])
    
    for record in attendance.order_by('-date', 'student__user__first_name'):
        writer.writerow([
            record.date,
            record.student.get_full_name(),
            record.student.admission_number,
            f"Form {record.class_level}",
            record.stream,
            record.get_status_display(),
            record.reason
        ])
    
    return response

# ============== Holiday Views ==============

@login_required
@admin_required
def holiday_list(request):
    """List holidays"""
    
    holidays = Holiday.objects.all().order_by('date')
    
    # Filter by year
    year = request.GET.get('year', timezone.now().year)
    holidays = holidays.filter(date__year=year)
    
    context = {
        'holidays': holidays,
        'year': year,
        'years': range(2020, timezone.now().year + 2),
    }
    
    return render(request, 'attendance/holiday_list.html', context)

@login_required
@admin_required
def holiday_create(request):
    """Create holiday"""
    
    if request.method == 'POST':
        form = HolidayForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Holiday added successfully.')
            return redirect('attendance:holiday_list')
    else:
        form = HolidayForm()
    
    return render(request, 'attendance/holiday_form.html', {
        'form': form,
        'title': 'Add Holiday'
    })

@login_required
@admin_required
def holiday_edit(request, holiday_id):
    """Edit holiday"""
    
    holiday = get_object_or_404(Holiday, id=holiday_id)
    
    if request.method == 'POST':
        form = HolidayForm(request.POST, instance=holiday)
        if form.is_valid():
            form.save()
            messages.success(request, 'Holiday updated.')
            return redirect('attendance:holiday_list')
    else:
        form = HolidayForm(instance=holiday)
    
    return render(request, 'attendance/holiday_form.html', {
        'form': form,
        'holiday': holiday,
        'title': 'Edit Holiday'
    })

@login_required
@admin_required
def holiday_delete(request, holiday_id):
    """Delete holiday"""
    
    holiday = get_object_or_404(Holiday, id=holiday_id)
    
    if request.method == 'POST':
        holiday.delete()
        messages.success(request, 'Holiday deleted.')
        return redirect('attendance:holiday_list')
    
    return render(request, 'attendance/holiday_confirm_delete.html', {'holiday': holiday})

# ============== Notification Views ==============

@login_required
def send_notifications(request):
    """Send attendance notifications"""
    
    if request.method == 'POST':
        # Get absent students for today
        today = timezone.now().date()
        absent_students = Attendance.objects.filter(
            date=today,
            status='absent'
        ).select_related('student')
        
        sent_count = 0
        for attendance in absent_students:
            # Send SMS to parent
            success = NotificationService.send_attendance_sms(attendance)
            if success:
                sent_count += 1
        
        messages.success(request, f'Sent {sent_count} notifications.')
        return redirect('attendance:attendance_dashboard')
    
    return render(request, 'attendance/send_notifications.html')

@login_required
def notification_list(request):
    """List attendance notifications"""
    
    notifications = AttendanceNotification.objects.all().select_related(
        'student', 'attendance'
    ).order_by('-created_at')
    
    paginator = Paginator(notifications, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
    }
    
    return render(request, 'attendance/notification_list.html', context)

# ============== API Views ==============

@login_required
def get_students_for_class(request):
    """API endpoint to get students for a class"""
    
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        class_level = request.GET.get('class_level')
        stream = request.GET.get('stream')
        
        students = Student.objects.filter(
            current_class=class_level,
            stream=stream,
            is_active=True
        ).values('id', 'user__first_name', 'user__last_name', 'admission_number')
        
        return JsonResponse(list(students), safe=False)
    
    return JsonResponse({'error': 'Invalid request'}, status=400)

@login_required
def get_attendance_summary(request):
    """API endpoint to get attendance summary"""
    
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        date = request.GET.get('date', timezone.now().date().isoformat())
        
        summary = AttendanceService.get_daily_summary(date)
        return JsonResponse(summary)
    
    return JsonResponse({'error': 'Invalid request'}, status=400)