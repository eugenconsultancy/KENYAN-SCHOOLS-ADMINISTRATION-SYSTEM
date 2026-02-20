from django.db.models import Count, Avg, Sum, Q
from django.utils import timezone
from .models import Student, Club, Sport
from academics.models import Result, Term, AcademicYear
from attendance.models import Attendance
from finance.models import Payment, Invoice
import datetime

class StudentService:
    """Service class for student-related business logic"""
    
    @staticmethod
    def get_student_statistics():
        """Get overall student statistics"""
        total_students = Student.objects.count()
        active_students = Student.objects.filter(is_active=True).count()
        
        # Gender distribution
        male_count = Student.objects.filter(gender='M').count()
        female_count = Student.objects.filter(gender='F').count()
        
        # Class distribution
        class_distribution = Student.objects.values('current_class').annotate(
            count=Count('id')
        ).order_by('current_class')
        
        # Stream distribution
        stream_distribution = Student.objects.values('stream').annotate(
            count=Count('id')
        ).order_by('stream')
        
        # Boarding status
        boarders = Student.objects.filter(boarding_status='boarder').count()
        day_scholars = Student.objects.filter(boarding_status='day_scholar').count()
        
        return {
            'total_students': total_students,
            'active_students': active_students,
            'male_count': male_count,
            'female_count': female_count,
            'class_distribution': class_distribution,
            'stream_distribution': stream_distribution,
            'boarders': boarders,
            'day_scholars': day_scholars,
        }
    
    @staticmethod
    def get_student_performance(student, term=None):
        """Get performance statistics for a student"""
        if not term:
            # Get current term
            current_year = AcademicYear.objects.filter(is_current=True).first()
            if current_year:
                term = Term.objects.filter(academic_year=current_year, is_current=True).first()
        
        if term:
            results = Result.objects.filter(student=student, term=term)
            subjects = results.count()
            
            if subjects > 0:
                total_marks = results.aggregate(total=Sum('marks'))['total']
                average = total_marks / subjects
                
                # Get subject performance
                subject_performance = []
                for result in results:
                    subject_performance.append({
                        'subject': result.subject.name,
                        'marks': result.marks,
                        'grade': result.get_grade_display(),
                        'points': result.points,
                    })
                
                return {
                    'term': str(term),
                    'subjects': subjects,
                    'total_marks': total_marks,
                    'average': average,
                    'mean_grade': student.get_mean_grade(term),
                    'subject_performance': subject_performance,
                }
        
        return None
    
    @staticmethod
    def get_student_attendance_summary(student, start_date=None, end_date=None):
        """Get attendance summary for a student"""
        attendance = Attendance.objects.filter(student=student)
        
        if start_date:
            attendance = attendance.filter(date__gte=start_date)
        if end_date:
            attendance = attendance.filter(date__lte=end_date)
        
        total_days = attendance.count()
        present = attendance.filter(status='present').count()
        absent = attendance.filter(status='absent').count()
        late = attendance.filter(status='late').count()
        excused = attendance.filter(status='excused').count()
        
        return {
            'total_days': total_days,
            'present': present,
            'absent': absent,
            'late': late,
            'excused': excused,
            'attendance_percentage': (present / total_days * 100) if total_days > 0 else 0,
        }
    
    @staticmethod
    def get_student_financial_summary(student):
        """Get financial summary for a student"""
        # Get all invoices
        invoices = Invoice.objects.filter(student=student)
        total_invoiced = invoices.aggregate(total=Sum('amount'))['total'] or 0
        
        # Get all payments
        payments = Payment.objects.filter(student=student)
        total_paid = payments.aggregate(total=Sum('amount'))['total'] or 0
        
        # Get outstanding balance
        outstanding = total_invoiced - total_paid
        
        # Get payment history
        payment_history = payments.order_by('-payment_date')[:10]
        
        return {
            'total_invoiced': total_invoiced,
            'total_paid': total_paid,
            'outstanding': outstanding,
            'payment_history': payment_history,
        }
    
    @staticmethod
    def get_students_by_class(class_level, stream=None):
        """Get students by class and optionally stream"""
        students = Student.objects.filter(current_class=class_level, is_active=True)
        if stream:
            students = students.filter(stream=stream)
        return students.order_by('stream', 'user__first_name')
    
    @staticmethod
    def search_students(query):
        """Search students by various fields"""
        return Student.objects.filter(
            Q(admission_number__icontains=query) |
            Q(kcpe_index__icontains=query) |
            Q(user__first_name__icontains=query) |
            Q(user__last_name__icontains=query) |
            Q(parent_name__icontains=query) |
            Q(parent_phone__icontains=query)
        ).filter(is_active=True)
    
    @staticmethod
    def get_top_performers(class_level=None, limit=10):
        """Get top performing students"""
        # This would require a more complex query with ranking
        # Simplified version - get students with highest average marks
        current_year = AcademicYear.objects.filter(is_current=True).first()
        if current_year:
            current_term = Term.objects.filter(academic_year=current_year, is_current=True).first()
            
            if current_term:
                students = Student.objects.filter(is_active=True)
                if class_level:
                    students = students.filter(current_class=class_level)
                
                # This is a simplified approach - in production you'd want to use a more efficient method
                top_students = []
                for student in students:
                    results = Result.objects.filter(student=student, term=current_term)
                    if results.exists():
                        avg = results.aggregate(Avg('marks'))['marks__avg']
                        top_students.append({
                            'student': student,
                            'average': avg
                        })
                
                top_students.sort(key=lambda x: x['average'], reverse=True)
                return top_students[:limit]
        
        return []
    
    @staticmethod
    def get_birthday_students(month=None):
        """Get students with birthdays in given month"""
        if not month:
            month = timezone.now().month
        
        return Student.objects.filter(
            date_of_birth__month=month,
            is_active=True
        ).order_by('date_of_birth')
    
    @staticmethod
    def promote_students():
        """Promote all students to next class at end of year"""
        students = Student.objects.filter(is_active=True)
        promoted = 0
        graduates = 0
        
        for student in students:
            if student.current_class == 4:  # Form 4 graduates
                student.is_active = False
                student.save()
                graduates += 1
            else:
                student.current_class += 1
                student.save()
                promoted += 1
        
        return {
            'promoted': promoted,
            'graduates': graduates
        }