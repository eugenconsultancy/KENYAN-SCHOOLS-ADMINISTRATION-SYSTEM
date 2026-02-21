from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Sum, Avg, Q
from django.utils import timezone
from accounts.decorators import role_required
from students.models import Student
from teachers.models import Teacher
from academics.models import Term, Result, Exam, Class
from finance.models import Invoice, Payment
from attendance.models import Attendance
from messaging.models import Notification, Message
import json
import datetime

@login_required
def home(request):
    """Main dashboard view - role-based redirection"""
    
    if request.user.role == 'admin':
        return admin_dashboard(request)
    elif request.user.role == 'teacher':
        return teacher_dashboard(request)
    elif request.user.role == 'student':
        return student_dashboard(request)
    elif request.user.role == 'parent':
        return parent_dashboard(request)
    elif request.user.role == 'accountant':
        return accountant_dashboard(request)
    else:
        return render(request, 'dashboard/home.html')

@login_required
@role_required(['admin'])
def admin_dashboard(request):
    """Admin dashboard with school-wide statistics"""
    
    today = timezone.now().date()
    current_term = Term.objects.filter(is_current=True).first()
    
    # Student statistics
    total_students = Student.objects.count()
    active_students = Student.objects.filter(is_active=True).count()
    male_students = Student.objects.filter(gender='M', is_active=True).count()
    female_students = Student.objects.filter(gender='F', is_active=True).count()
    
    # Class distribution
    class_distribution = []
    for class_level in range(1, 5):
        count = Student.objects.filter(current_class=class_level, is_active=True).count()
        class_distribution.append({
            'class': f'Form {class_level}',
            'count': count
        })
    
    # Teacher statistics
    total_teachers = Teacher.objects.count()
    active_teachers = Teacher.objects.filter(is_active=True).count()
    
    # Financial summary
    total_invoiced = Invoice.objects.aggregate(total=Sum('total_amount'))['total'] or 0
    total_collected = Payment.objects.filter(
        payment_status='completed'
    ).aggregate(total=Sum('amount'))['total'] or 0
    outstanding = total_invoiced - total_collected
    
    # Monthly collections for chart
    monthly_collections = []
    for month in range(1, 13):
        amount = Payment.objects.filter(
            payment_status='completed',
            payment_date__year=today.year,
            payment_date__month=month
        ).aggregate(total=Sum('amount'))['total'] or 0
        monthly_collections.append(float(amount))
    
    # Today's attendance
    today_attendance = Attendance.objects.filter(date=today)
    total_present = today_attendance.filter(status='present').count()
    total_absent = today_attendance.filter(status='absent').count()
    total_late = today_attendance.filter(status='late').count()
    total_records = today_attendance.count()
    
    # Upcoming exams
    upcoming_exams = Exam.objects.filter(
        start_date__gte=today
    ).order_by('start_date')[:5]
    
    # Recent activities (notifications/messages)
    recent_notifications = Notification.objects.all().order_by('-created_at')[:10]
    
    # Performance summary (if current term exists)
    performance_summary = {}
    if current_term:
        for class_level in range(1, 5):
            avg = Result.objects.filter(
                student__current_class=class_level,
                exam__term=current_term
            ).aggregate(Avg('marks'))['marks__avg']
            performance_summary[f'Form {class_level}'] = round(avg, 1) if avg else 0
    
    context = {
        'total_students': total_students,
        'active_students': active_students,
        'male_students': male_students,
        'female_students': female_students,
        'class_distribution': class_distribution,
        'total_teachers': total_teachers,
        'active_teachers': active_teachers,
        'total_invoiced': float(total_invoiced),
        'total_collected': float(total_collected),
        'outstanding': float(outstanding),
        'monthly_collections': json.dumps(monthly_collections),
        'today_attendance': {
            'present': total_present,
            'absent': total_absent,
            'late': total_late,
            'total': total_records,
        },
        'upcoming_exams': upcoming_exams,
        'recent_notifications': recent_notifications,
        'performance_summary': performance_summary,
        'current_term': current_term,
    }
    
    return render(request, 'dashboard/admin_dashboard.html', context)

@login_required
@role_required(['teacher'])
def teacher_dashboard(request):
    """Teacher dashboard"""
    
    # Check if user has teacher profile
    try:
        teacher = request.user.teacher_profile
    except Teacher.DoesNotExist:
        return render(request, 'dashboard/error.html', {
            'error_message': 'Teacher profile not found. Please contact administrator.'
        })
    
    today = timezone.now().date()
    current_term = Term.objects.filter(is_current=True).first()
    
    # Classes taught by this teacher
    taught_classes = teacher.subject_allocations.values_list('class_assigned', flat=True).distinct()
    classes = Class.objects.filter(id__in=taught_classes)
    
    # Subjects taught
    subjects = teacher.subjects_taught.select_related('subject').all()
    
    # My form classes (if any)
    form_classes = teacher.form_classes.filter(is_current=True)
    
    # Today's classes (from timetable)
    from academics.models import Timetable
    today_classes = Timetable.objects.filter(
        teacher=teacher,
        day=today.weekday() + 1  # Monday=1 in our model
    ).select_related('subject', 'class_assigned')
    
    # Recent messages
    recent_messages = Message.objects.filter(
        conversation__participants=request.user
    ).exclude(
        sender=request.user
    ).order_by('-created_at')[:5]
    
    # Pending tasks (attendance to mark, results to enter)
    pending_attendance = 0
    pending_results = 0
    
    if form_classes:
        for form_class in form_classes:
            # Check if attendance not marked for today
            marked = Attendance.objects.filter(
                class_level=form_class.class_level,
                stream=form_class.stream,
                date=today
            ).exists()
            if not marked:
                pending_attendance += 1
    
    # Results pending entry for recent exams
    if current_term and subjects:
        exams = Exam.objects.filter(term=current_term, subjects__in=[s.subject for s in subjects])
        for exam in exams:
            # Check if results entered for all students in classes
            for class_obj in classes:
                students = Student.objects.filter(
                    current_class=class_obj.class_level,
                    stream=class_obj.stream,
                    is_active=True
                )
                results_count = Result.objects.filter(
                    exam=exam,
                    student__in=students
                ).count()
                if results_count < students.count():
                    pending_results += 1
    
    context = {
        'teacher': teacher,
        'classes': classes,
        'subjects': subjects,
        'form_classes': form_classes,
        'today_classes': today_classes,
        'recent_messages': recent_messages,
        'pending_attendance': pending_attendance,
        'pending_results': pending_results,
        'current_term': current_term,
    }
    
    return render(request, 'dashboard/teacher_dashboard.html', context)

@login_required
@role_required(['student'])
def student_dashboard(request):
    """Student dashboard"""
    
    # Check if user has student profile
    try:
        student = request.user.student_profile
    except Student.DoesNotExist:
        return render(request, 'dashboard/error.html', {
            'error_message': 'Student profile not found. Please contact administrator.'
        })
    
    today = timezone.now().date()
    current_term = Term.objects.filter(is_current=True).first()
    
    # Academic performance
    recent_results = Result.objects.filter(
        student=student
    ).select_related('subject', 'exam').order_by('-exam__start_date')[:10]
    
    # Calculate average for current term
    if current_term:
        term_results = Result.objects.filter(
            student=student,
            exam__term=current_term
        )
        term_average = term_results.aggregate(Avg('marks'))['marks__avg'] or 0
        term_subjects = term_results.count()
    else:
        term_average = 0
        term_subjects = 0
    
    # Attendance summary
    attendance = Attendance.objects.filter(student=student)
    total_days = attendance.count()
    present_days = attendance.filter(status='present').count()
    attendance_rate = (present_days / total_days * 100) if total_days > 0 else 0
    
    # Financial summary
    invoices = Invoice.objects.filter(student=student)
    total_invoiced = invoices.aggregate(total=Sum('total_amount'))['total'] or 0
    total_paid = Payment.objects.filter(
        student=student,
        payment_status='completed'
    ).aggregate(total=Sum('amount'))['total'] or 0
    balance = total_invoiced - total_paid
    
    # Upcoming exams
    upcoming_exams = Exam.objects.filter(
        term=current_term,
        start_date__gte=today
    ).order_by('start_date')[:5]
    
    # Today's timetable
    from academics.models import Timetable
    today_classes = Timetable.objects.filter(
        class_assigned__class_level=student.current_class,
        class_assigned__stream=student.stream,
        day=today.weekday() + 1
    ).select_related('subject', 'teacher')
    
    # Recent announcements
    from messaging.models import Announcement
    announcements = Announcement.objects.filter(
        Q(audience_type='all') |
        Q(audience_type='students') |
        Q(audience_type='class', target_class_level=student.current_class)
    ).filter(
        Q(expiry_date__gte=today) | Q(expiry_date__isnull=True),
        publish_date__lte=today
    ).order_by('-publish_date')[:5]
    
    # Unread notifications count - FIXED: changed from 'notifications' to 'account_notifications'
    unread_notifications = request.user.account_notifications.filter(is_read=False).count()
    
    # Clubs and sports
    clubs = student.clubs.all()
    sports = student.sports.all()
    
    context = {
        'student': student,
        'recent_results': recent_results,
        'term_average': round(term_average, 1) if term_average else 0,
        'term_subjects': term_subjects,
        'attendance_rate': round(attendance_rate, 1),
        'present_days': present_days,
        'total_days': total_days,
        'balance': float(balance),
        'total_paid': float(total_paid),
        'upcoming_exams': upcoming_exams,
        'today_classes': today_classes,
        'announcements': announcements,
        'unread_notifications': unread_notifications,
        'current_term': current_term,
        'clubs': clubs,
        'sports': sports,
    }
    
    return render(request, 'dashboard/student_dashboard.html', context)

@login_required
@role_required(['parent'])
def parent_dashboard(request):
    """Parent dashboard - view their children's progress"""
    
    # Check if user has parent profile
    try:
        parent = request.user.parent_profile
    except:
        return render(request, 'dashboard/error.html', {
            'error_message': 'Parent profile not found. Please contact administrator.'
        })
    
    children = parent.students.filter(is_active=True)
    
    children_data = []
    
    for child in children:
        # Get academic performance
        recent_results = Result.objects.filter(
            student=child
        ).select_related('subject', 'exam').order_by('-exam__start_date')[:5]
        
        # Attendance
        attendance = Attendance.objects.filter(student=child)
        total_days = attendance.count()
        present_days = attendance.filter(status='present').count()
        attendance_rate = (present_days / total_days * 100) if total_days > 0 else 0
        
        # Financial
        invoices = Invoice.objects.filter(student=child)
        total_invoiced = invoices.aggregate(total=Sum('total_amount'))['total'] or 0
        total_paid = Payment.objects.filter(
            student=child,
            payment_status='completed'
        ).aggregate(total=Sum('amount'))['total'] or 0
        balance = total_invoiced - total_paid
        
        # Upcoming exams
        current_term = Term.objects.filter(is_current=True).first()
        upcoming_exams = Exam.objects.filter(
            term=current_term
        ).order_by('start_date')[:3]
        
        children_data.append({
            'student': child,
            'recent_results': recent_results,
            'attendance_rate': round(attendance_rate, 1),
            'balance': float(balance),
            'upcoming_exams': upcoming_exams,
        })
    
    # Recent messages from school
    recent_messages = Message.objects.filter(
        conversation__participants=request.user
    ).order_by('-created_at')[:5]
    
    context = {
        'children': children_data,
        'recent_messages': recent_messages,
    }
    
    return render(request, 'dashboard/parent_dashboard.html', context)

@login_required
@role_required(['accountant'])
def accountant_dashboard(request):
    """Accountant dashboard"""
    
    today = timezone.now().date()
    
    # Financial overview
    total_invoiced = Invoice.objects.aggregate(total=Sum('total_amount'))['total'] or 0
    total_collected = Payment.objects.filter(
        payment_status='completed'
    ).aggregate(total=Sum('amount'))['total'] or 0
    outstanding = total_invoiced - total_collected
    
    # Today's collections
    today_collected = Payment.objects.filter(
        payment_status='completed',
        payment_date__date=today
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    # Overdue invoices
    overdue_invoices = Invoice.objects.filter(
        status='overdue',
        balance__gt=0
    ).count()
    overdue_amount = Invoice.objects.filter(
        status='overdue',
        balance__gt=0
    ).aggregate(total=Sum('balance'))['total'] or 0
    
    # Recent payments
    recent_payments = Payment.objects.filter(
        payment_status='completed'
    ).select_related('student').order_by('-payment_date')[:10]
    
    # Class-wise fee collection
    class_collection = []
    for class_level in range(1, 5):
        students = Student.objects.filter(current_class=class_level, is_active=True)
        student_ids = students.values_list('id', flat=True)
        
        collected = Payment.objects.filter(
            student_id__in=student_ids,
            payment_status='completed'
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        invoiced = Invoice.objects.filter(
            student_id__in=student_ids
        ).aggregate(total=Sum('total_amount'))['total'] or 0
        
        class_collection.append({
            'class': f'Form {class_level}',
            'invoiced': float(invoiced),
            'collected': float(collected),
            'outstanding': float(invoiced - collected)
        })
    
    # Monthly collection chart
    monthly_collections = []
    for month in range(1, 13):
        amount = Payment.objects.filter(
            payment_status='completed',
            payment_date__year=today.year,
            payment_date__month=month
        ).aggregate(total=Sum('amount'))['total'] or 0
        monthly_collections.append(float(amount))
    
    # Top defaulters
    top_defaulters = Invoice.objects.filter(
        status='overdue',
        balance__gt=0
    ).values('student__user__first_name', 'student__user__last_name', 'student__admission_number').annotate(
        total_balance=Sum('balance')
    ).order_by('-total_balance')[:5]
    
    context = {
        'total_invoiced': float(total_invoiced),
        'total_collected': float(total_collected),
        'outstanding': float(outstanding),
        'today_collected': float(today_collected),
        'overdue_invoices': overdue_invoices,
        'overdue_amount': float(overdue_amount),
        'recent_payments': recent_payments,
        'class_collection': class_collection,
        'monthly_collections': json.dumps(monthly_collections),
        'top_defaulters': top_defaulters,
    }
    
    return render(request, 'dashboard/accountant_dashboard.html', context)

@login_required
def get_chart_data(request):
    """API endpoint for dashboard charts"""
    
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        chart_type = request.GET.get('type')
        period = request.GET.get('period', 'month')
        
        data = {}
        
        if chart_type == 'attendance':
            # Attendance trend
            days = 30 if period == 'month' else 7
            end_date = timezone.now().date()
            start_date = end_date - timezone.timedelta(days=days)
            
            dates = []
            present_counts = []
            
            current = start_date
            while current <= end_date:
                dates.append(current.strftime('%Y-%m-%d'))
                present = Attendance.objects.filter(
                    date=current,
                    status='present'
                ).count()
                present_counts.append(present)
                current += timezone.timedelta(days=1)
            
            data = {
                'labels': dates,
                'datasets': [{
                    'label': 'Present Students',
                    'data': present_counts,
                    'borderColor': 'rgb(75, 192, 192)',
                    'tension': 0.1
                }]
            }
        
        elif chart_type == 'fees':
            # Fee collection by class
            labels = []
            collected_data = []
            outstanding_data = []
            
            for class_level in range(1, 5):
                labels.append(f'Form {class_level}')
                students = Student.objects.filter(current_class=class_level, is_active=True)
                student_ids = students.values_list('id', flat=True)
                
                collected = Payment.objects.filter(
                    student_id__in=student_ids,
                    payment_status='completed'
                ).aggregate(total=Sum('amount'))['total'] or 0
                
                invoiced = Invoice.objects.filter(
                    student_id__in=student_ids
                ).aggregate(total=Sum('total_amount'))['total'] or 0
                
                collected_data.append(float(collected))
                outstanding_data.append(float(invoiced - collected))
            
            data = {
                'labels': labels,
                'datasets': [
                    {
                        'label': 'Collected',
                        'data': collected_data,
                        'backgroundColor': 'rgba(54, 162, 235, 0.5)',
                    },
                    {
                        'label': 'Outstanding',
                        'data': outstanding_data,
                        'backgroundColor': 'rgba(255, 99, 132, 0.5)',
                    }
                ]
            }
        
        elif chart_type == 'performance':
            # Academic performance by class
            current_term = Term.objects.filter(is_current=True).first()
            if current_term:
                labels = []
                averages = []
                
                for class_level in range(1, 5):
                    labels.append(f'Form {class_level}')
                    avg = Result.objects.filter(
                        student__current_class=class_level,
                        exam__term=current_term
                    ).aggregate(Avg('marks'))['marks__avg'] or 0
                    averages.append(round(avg, 1))
                
                data = {
                    'labels': labels,
                    'datasets': [{
                        'label': 'Average Score',
                        'data': averages,
                        'backgroundColor': 'rgba(255, 159, 64, 0.5)',
                    }]
                }
        
        return JsonResponse(data)
    
    return JsonResponse({'error': 'Invalid request'}, status=400)