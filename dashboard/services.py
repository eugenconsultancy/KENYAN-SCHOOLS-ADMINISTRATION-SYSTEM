"""
Services module for Dashboard app
Handles data aggregation for dashboards
"""

from django.db.models import Count, Sum, Avg, Q
from django.utils import timezone
from students.models import Student
from teachers.models import Teacher
from academics.models import Term, Result, Exam, Class
from finance.models import Invoice, Payment
from attendance.models import Attendance
from messaging.models import Notification
import datetime

class DashboardService:
    """Service for dashboard data aggregation"""
    
    @staticmethod
    def get_school_stats():
        """Get overall school statistics"""
        
        # Student stats
        total_students = Student.objects.count()
        active_students = Student.objects.filter(is_active=True).count()
        male_students = Student.objects.filter(gender='M', is_active=True).count()
        female_students = Student.objects.filter(gender='F', is_active=True).count()
        
        # Teacher stats
        total_teachers = Teacher.objects.count()
        active_teachers = Teacher.objects.filter(is_active=True).count()
        
        # Class distribution
        class_distribution = []
        for level in range(1, 5):
            count = Student.objects.filter(current_class=level, is_active=True).count()
            class_distribution.append({
                'class': f'Form {level}',
                'count': count
            })
        
        return {
            'total_students': total_students,
            'active_students': active_students,
            'male_students': male_students,
            'female_students': female_students,
            'total_teachers': total_teachers,
            'active_teachers': active_teachers,
            'class_distribution': class_distribution,
        }
    
    @staticmethod
    def get_financial_summary():
        """Get financial summary"""
        
        total_invoiced = Invoice.objects.aggregate(total=Sum('total_amount'))['total'] or 0
        total_collected = Payment.objects.filter(
            payment_status='completed'
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        return {
            'total_invoiced': total_invoiced,
            'total_collected': total_collected,
            'outstanding': total_invoiced - total_collected,
        }
    
    @staticmethod
    def get_attendance_today():
        """Get today's attendance summary"""
        
        today = timezone.now().date()
        attendance = Attendance.objects.filter(date=today)
        
        return {
            'total': attendance.count(),
            'present': attendance.filter(status='present').count(),
            'absent': attendance.filter(status='absent').count(),
            'late': attendance.filter(status='late').count(),
            'excused': attendance.filter(status__in=['excused', 'sick']).count(),
        }
    
    @staticmethod
    def get_term_performance(term=None):
        """Get performance summary for a term"""
        
        if not term:
            term = Term.objects.filter(is_current=True).first()
        
        if not term:
            return {}
        
        performance = {}
        for level in range(1, 5):
            avg = Result.objects.filter(
                student__current_class=level,
                exam__term=term
            ).aggregate(Avg('marks'))['marks__avg']
            
            if avg:
                performance[f'Form {level}'] = round(avg, 1)
        
        return performance
    
    @staticmethod
    def get_upcoming_events(days=7):
        """Get upcoming events (exams, holidays)"""
        
        today = timezone.now().date()
        end_date = today + timezone.timedelta(days=days)
        
        # Upcoming exams
        exams = Exam.objects.filter(
            start_date__gte=today,
            start_date__lte=end_date
        ).order_by('start_date')
        
        # Holidays (from attendance app)
        from attendance.models import Holiday
        holidays = Holiday.objects.filter(
            date__gte=today,
            date__lte=end_date
        ).order_by('date')
        
        events = []
        
        for exam in exams:
            events.append({
                'date': exam.start_date,
                'title': exam.name,
                'type': 'exam',
                'description': f"{exam.exam_type} - {exam.term}",
            })
        
        for holiday in holidays:
            events.append({
                'date': holiday.date,
                'title': holiday.name,
                'type': 'holiday',
                'description': holiday.holiday_type,
            })
        
        return sorted(events, key=lambda x: x['date'])
    
    @staticmethod
    def get_recent_activities(limit=10):
        """Get recent system activities"""
        
        activities = []
        
        # Recent payments
        payments = Payment.objects.filter(
            payment_status='completed'
        ).select_related('student').order_by('-payment_date')[:5]
        
        for payment in payments:
            activities.append({
                'timestamp': payment.payment_date,
                'type': 'payment',
                'description': f"Payment of KSh {payment.amount} from {payment.student.get_full_name()}",
                'icon': 'money',
            })
        
        # Recent student additions
        students = Student.objects.order_by('-created_at')[:5]
        for student in students:
            activities.append({
                'timestamp': student.created_at,
                'type': 'student',
                'description': f"New student added: {student.get_full_name()}",
                'icon': 'user',
            })
        
        # Recent teacher additions
        teachers = Teacher.objects.order_by('-created_at')[:5]
        for teacher in teachers:
            activities.append({
                'timestamp': teacher.created_at,
                'type': 'teacher',
                'description': f"New teacher added: {teacher.get_full_name()}",
                'icon': 'teacher',
            })
        
        # Sort by timestamp
        activities.sort(key=lambda x: x['timestamp'], reverse=True)
        
        return activities[:limit]
    
    @staticmethod
    def get_student_performance_trend(student_id, num_terms=3):
        """Get performance trend for a student"""
        
        from academics.models import ResultSummary
        
        summaries = ResultSummary.objects.filter(
            student_id=student_id
        ).select_related('term').order_by('-term__academic_year', '-term__term')[:num_terms]
        
        trend = []
        for summary in summaries:
            trend.append({
                'term': str(summary.term),
                'average': float(summary.average),
                'mean_grade': summary.mean_grade,
                'position': summary.position_in_class,
            })
        
        return trend
    
    @staticmethod
    def get_class_performance_comparison(term_id):
        """Compare performance across classes"""
        
        comparison = []
        
        for level in range(1, 5):
            for stream in ['East', 'West', 'North', 'South']:
                students = Student.objects.filter(
                    current_class=level,
                    stream=stream,
                    is_active=True
                )
                
                if students.exists():
                    results = Result.objects.filter(
                        student__in=students,
                        exam__term_id=term_id
                    )
                    
                    if results.exists():
                        avg = results.aggregate(Avg('marks'))['marks__avg']
                        comparison.append({
                            'class': f"Form {level} {stream}",
                            'average': round(avg, 1),
                            'student_count': students.count(),
                        })
        
        return sorted(comparison, key=lambda x: x['average'], reverse=True)