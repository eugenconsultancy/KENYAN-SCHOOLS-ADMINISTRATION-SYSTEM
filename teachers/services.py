from django.db.models import Count, Avg, Sum, Q
from django.utils import timezone
from .models import Teacher, TeacherLeave, TeacherAttendance, TeacherPerformance
from academics.models import Subject, Class as SchoolClass
import datetime

class TeacherService:
    """Service class for teacher-related business logic"""
    
    @staticmethod
    def get_teacher_statistics():
        """Get overall teacher statistics"""
        total_teachers = Teacher.objects.count()
        active_teachers = Teacher.objects.filter(is_active=True).count()
        
        # Gender distribution
        male_count = Teacher.objects.filter(gender='M').count()
        female_count = Teacher.objects.filter(gender='F').count()
        
        # Employment type distribution
        employment_distribution = Teacher.objects.values('employment_type').annotate(
            count=Count('id')
        ).order_by('employment_type')
        
        # Qualification distribution
        qualification_distribution = Teacher.objects.values('qualification_level').annotate(
            count=Count('id')
        ).order_by('qualification_level')
        
        return {
            'total_teachers': total_teachers,
            'active_teachers': active_teachers,
            'male_count': male_count,
            'female_count': female_count,
            'employment_distribution': employment_distribution,
            'qualification_distribution': qualification_distribution,
        }
    
    @staticmethod
    def get_teacher_attendance_summary(teacher, start_date=None, end_date=None):
        """Get attendance summary for a teacher"""
        attendance = TeacherAttendance.objects.filter(teacher=teacher)
        
        if start_date:
            attendance = attendance.filter(date__gte=start_date)
        if end_date:
            attendance = attendance.filter(date__lte=end_date)
        
        total_days = attendance.count()
        present = attendance.filter(status='present').count()
        absent = attendance.filter(status='absent').count()
        late = attendance.filter(status='late').count()
        leave = attendance.filter(status='leave').count()
        official = attendance.filter(status='official').count()
        
        return {
            'total_days': total_days,
            'present': present,
            'absent': absent,
            'late': late,
            'leave': leave,
            'official': official,
            'attendance_percentage': (present / total_days * 100) if total_days > 0 else 0,
        }
    
    @staticmethod
    def get_teacher_leave_summary(teacher, year=None):
        """Get leave summary for a teacher"""
        if not year:
            year = timezone.now().year
        
        leaves = TeacherLeave.objects.filter(
            teacher=teacher,
            start_date__year=year
        )
        
        approved_leaves = leaves.filter(status='approved')
        total_days = approved_leaves.aggregate(total=Sum('days_requested'))['total'] or 0
        
        # Group by leave type
        leave_by_type = approved_leaves.values('leave_type').annotate(
            days=Sum('days_requested')
        ).order_by('leave_type')
        
        return {
            'total_requests': leaves.count(),
            'approved_requests': approved_leaves.count(),
            'pending_requests': leaves.filter(status='pending').count(),
            'total_days': total_days,
            'leave_by_type': leave_by_type,
        }
    
    @staticmethod
    def get_teacher_performance_summary(teacher):
        """Get performance summary for a teacher"""
        performances = TeacherPerformance.objects.filter(teacher=teacher).order_by('-evaluation_date')
        
        if performances.exists():
            latest = performances.first()
            average_ratings = {
                'lesson_preparation': latest.lesson_preparation,
                'lesson_delivery': latest.lesson_delivery,
                'student_assessment': latest.student_assessment,
                'class_management': latest.class_management,
                'punctuality': latest.punctuality,
                'professional_conduct': latest.professional_conduct,
                'co_curricular': latest.co_curricular,
                'overall': latest.get_average_rating(),
            }
            
            # Get trend (compare with previous)
            if performances.count() > 1:
                previous = performances[1]
                trend = latest.get_average_rating() - previous.get_average_rating()
            else:
                trend = 0
            
            return {
                'has_performance': True,
                'latest': latest,
                'ratings': average_ratings,
                'trend': trend,
                'total_evaluations': performances.count(),
            }
        
        return {'has_performance': False}
    
    @staticmethod
    def get_teachers_by_department(department):
        """Get teachers by department/subject area"""
        # This would need a department model
        pass
    
    @staticmethod
    def search_teachers(query):
        """Search teachers by various fields"""
        return Teacher.objects.filter(
            Q(employee_number__icontains=query) |
            Q(tsc_number__icontains=query) |
            Q(id_number__icontains=query) |
            Q(user__first_name__icontains=query) |
            Q(user__last_name__icontains=query) |
            Q(phone_number__icontains=query)
        ).filter(is_active=True)
    
    @staticmethod
    def get_birthday_teachers(month=None):
        """Get teachers with birthdays in given month"""
        if not month:
            month = timezone.now().month
        
        return Teacher.objects.filter(
            date_of_birth__month=month,
            is_active=True
        ).order_by('date_of_birth')
    
    @staticmethod
    def get_teachers_on_leave():
        """Get teachers currently on leave"""
        today = timezone.now().date()
        return Teacher.objects.filter(
            leaves__start_date__lte=today,
            leaves__end_date__gte=today,
            leaves__status='approved'
        ).distinct()
    
    @staticmethod
    def get_workload_distribution():
        """Get distribution of teaching workload"""
        teachers = Teacher.objects.filter(is_active=True)
        workload = []
        
        for teacher in teachers:
            subject_count = teacher.subjects_taught.count()
            class_count = teacher.form_classes.filter(is_current=True).count()
            
            workload.append({
                'teacher': teacher.get_full_name(),
                'subjects': subject_count,
                'classes': class_count,
            })
        
        return sorted(workload, key=lambda x: x['subjects'], reverse=True)
    
    @staticmethod
    def calculate_salary_summary(year=None):
        """Calculate salary summary for a given year"""
        if not year:
            year = timezone.now().year
        
        salaries = TeacherSalary.objects.filter(year=year)
        
        total_basic = salaries.aggregate(total=Sum('basic_salary'))['total'] or 0
        total_allowances = salaries.aggregate(
            total=Sum('house_allowance') + Sum('transport_allowance') + 
                  Sum('medical_allowance') + Sum('other_allowances')
        )['total'] or 0
        total_deductions = salaries.aggregate(
            total=Sum('tax') + Sum('nhif') + Sum('nssf') + 
                  Sum('loan_deduction') + Sum('other_deductions')
        )['total'] or 0
        total_net = salaries.aggregate(total=Sum('net_salary'))['total'] or 0
        
        # Monthly breakdown
        monthly = []
        for month in range(1, 13):
            month_salaries = salaries.filter(month=month)
            if month_salaries.exists():
                monthly.append({
                    'month': month,
                    'count': month_salaries.count(),
                    'total': month_salaries.aggregate(total=Sum('net_salary'))['total'] or 0,
                })
        
        return {
            'total_salaries': salaries.count(),
            'total_basic': total_basic,
            'total_allowances': total_allowances,
            'total_deductions': total_deductions,
            'total_net': total_net,
            'monthly_breakdown': monthly,
        }