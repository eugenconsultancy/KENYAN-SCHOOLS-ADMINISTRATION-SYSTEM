"""
Services module for Academics app
Handles business logic for academic operations
"""

from django.db.models import Avg, Sum, Count, Q, F
from django.utils import timezone
from .models import (
    AcademicYear, Term, Subject, Class, SubjectAllocation,
    Exam, Result, ResultSummary, Homework, HomeworkSubmission
)
from students.models import Student
from teachers.models import Teacher
from .grading import GradingSystem, ReportCardGenerator
from .ranking import RankingService, PerformanceAnalyzer
import datetime
from decimal import Decimal

class AcademicYearService:
    """Service for academic year operations"""
    
    @staticmethod
    def get_current_academic_year():
        """Get the current academic year"""
        return AcademicYear.objects.filter(is_current=True).first()
    
    @staticmethod
    def get_current_term():
        """Get the current term"""
        return Term.objects.filter(is_current=True).first()
    
    @staticmethod
    def create_next_academic_year():
        """Create next academic year based on current one"""
        current = AcademicYear.objects.filter(is_current=True).first()
        if not current:
            return None
        
        # Calculate next year dates
        next_year = int(current.name) + 1
        start_date = current.start_date.replace(year=next_year)
        end_date = current.end_date.replace(year=next_year)
        
        # Create new academic year
        next_academic_year = AcademicYear.objects.create(
            name=str(next_year),
            start_date=start_date,
            end_date=end_date,
            is_current=False
        )
        
        # Create terms for next year
        current_terms = Term.objects.filter(academic_year=current)
        for term in current_terms:
            Term.objects.create(
                academic_year=next_academic_year,
                term=term.term,
                start_date=term.start_date.replace(year=next_year),
                end_date=term.end_date.replace(year=next_year),
                is_current=False
            )
        
        return next_academic_year
    
    @staticmethod
    def promote_students():
        """Promote all students to next class at end of year"""
        from students.models import Student
        
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

class TermService:
    """Service for term operations"""
    
    @staticmethod
    def get_term_dates(term, academic_year):
        """Get standard term dates for Kenyan schools"""
        # Standard Kenyan school term dates (approximate)
        term_dates = {
            1: {'start': '01-15', 'end': '04-15'},  # Term 1: Jan 15 - Apr 15
            2: {'start': '05-01', 'end': '08-15'},  # Term 2: May 1 - Aug 15
            3: {'start': '09-01', 'end': '11-30'},  # Term 3: Sep 1 - Nov 30
        }
        
        if term in term_dates:
            year = academic_year.start_date.year
            start_date = datetime.datetime.strptime(f"{year}-{term_dates[term]['start']}", "%Y-%m-%d").date()
            end_date = datetime.datetime.strptime(f"{year}-{term_dates[term]['end']}", "%Y-%m-%d").date()
            return start_date, end_date
        
        return None, None
    
    @staticmethod
    def calculate_term_weeks(term):
        """Calculate number of weeks in a term"""
        if term.start_date and term.end_date:
            delta = term.end_date - term.start_date
            return delta.days // 7
        return 0
    
    @staticmethod
    def get_remaining_weeks(term):
        """Get remaining weeks in current term"""
        if term.is_current and term.end_date:
            today = timezone.now().date()
            if today <= term.end_date:
                delta = term.end_date - today
                return max(0, delta.days // 7)
        return 0

class SubjectService:
    """Service for subject operations"""
    
    @staticmethod
    def get_subjects_for_class(class_level):
        """Get subjects offered in a specific class level"""
        return Subject.objects.filter(
            is_active=True,
            classes__contains=[class_level]
        ).order_by('category', 'name')
    
    @staticmethod
    def get_teacher_subjects(teacher_id):
        """Get subjects taught by a specific teacher"""
        return SubjectAllocation.objects.filter(
            teacher_id=teacher_id
        ).select_related('subject', 'class_assigned')
    
    @staticmethod
    def get_class_subjects(class_id):
        """Get subjects allocated to a specific class"""
        return SubjectAllocation.objects.filter(
            class_assigned_id=class_id
        ).select_related('subject', 'teacher')
    
    @staticmethod
    def calculate_subject_performance(subject_id, term_id):
        """Calculate performance statistics for a subject"""
        results = Result.objects.filter(
            subject_id=subject_id,
            exam__term_id=term_id
        )
        
        if not results.exists():
            return None
        
        marks = [r.marks for r in results]
        
        return {
            'mean': sum(marks) / len(marks),
            'median': sorted(marks)[len(marks) // 2],
            'max': max(marks),
            'min': min(marks),
            'pass_rate': sum(1 for m in marks if m >= 50) / len(marks) * 100,
            'total_students': len(marks),
        }

class ClassService:
    """Service for class operations"""
    
    @staticmethod
    def get_class_summary(class_id):
        """Get comprehensive summary for a class"""
        class_obj = Class.objects.get(id=class_id)
        
        students = Student.objects.filter(
            current_class=class_obj.class_level,
            stream=class_obj.stream,
            is_active=True
        )
        
        # Get current term
        current_term = Term.objects.filter(
            academic_year=class_obj.academic_year,
            is_current=True
        ).first()
        
        # Get subject allocations
        subjects = SubjectAllocation.objects.filter(
            class_assigned=class_obj
        ).select_related('subject', 'teacher')
        
        # Get performance if term exists
        performance = None
        if current_term:
            performance = PerformanceAnalyzer.analyze_class_performance(
                current_term, class_obj.class_level
            )
        
        return {
            'class': class_obj,
            'student_count': students.count(),
            'male_count': students.filter(gender='M').count(),
            'female_count': students.filter(gender='F').count(),
            'subjects': subjects,
            'current_term': current_term,
            'performance': performance,
            'capacity_percentage': class_obj.get_capacity_percentage(),
        }
    
    @staticmethod
    def get_class_teachers(class_id):
        """Get all teachers teaching in a class"""
        allocations = SubjectAllocation.objects.filter(
            class_assigned_id=class_id
        ).select_related('teacher').values('teacher').distinct()
        
        teacher_ids = [a['teacher'] for a in allocations if a['teacher']]
        return Teacher.objects.filter(id__in=teacher_ids)
    
    @staticmethod
    def generate_class_timetable(class_id, term_id):
        """Generate timetable for a class"""
        from .models import Timetable
        
        timetable = Timetable.objects.filter(
            class_assigned_id=class_id,
            term_id=term_id
        ).order_by('day', 'start_time')
        
        # Organize by day
        days = {i: [] for i in range(1, 6)}  # Monday to Friday
        for entry in timetable:
            days[entry.day].append(entry)
        
        return days

class ExamService:
    """Service for exam operations"""
    
    @staticmethod
    def get_upcoming_exams(days=7):
        """Get exams scheduled in the next X days"""
        today = timezone.now().date()
        end_date = today + datetime.timedelta(days=days)
        
        return ExamSchedule.objects.filter(
            date__gte=today,
            date__lte=end_date
        ).select_related('exam', 'subject', 'class_assigned').order_by('date', 'start_time')
    
    @staticmethod
    def get_exam_results_summary(exam_id):
        """Get summary of results for an exam"""
        results = Result.objects.filter(exam_id=exam_id)
        
        if not results.exists():
            return None
        
        # Overall statistics
        total_marks = sum(r.marks for r in results)
        average = total_marks / len(results)
        
        # Subject breakdown
        subject_stats = {}
        for result in results:
            subject_name = result.subject.name
            if subject_name not in subject_stats:
                subject_stats[subject_name] = {
                    'total': 0,
                    'count': 0,
                    'marks': []
                }
            subject_stats[subject_name]['total'] += result.marks
            subject_stats[subject_name]['count'] += 1
            subject_stats[subject_name]['marks'].append(result.marks)
        
        # Calculate means
        for subject, stats in subject_stats.items():
            stats['mean'] = stats['total'] / stats['count']
            stats['pass_rate'] = sum(1 for m in stats['marks'] if m >= 50) / stats['count'] * 100
        
        return {
            'total_results': len(results),
            'overall_average': average,
            'subject_stats': subject_stats,
        }
    
    @staticmethod
    def publish_exam_results(exam_id):
        """Publish exam results and update rankings"""
        exam = Exam.objects.get(id=exam_id)
        exam.is_published = True
        exam.save()
        
        # Update result summaries for affected students
        term = exam.term
        RankingService.update_term_summaries(term)
        
        return exam

class HomeworkService:
    """Service for homework operations"""
    
    @staticmethod
    def get_pending_homework(student_id):
        """Get pending homework for a student"""
        student = Student.objects.get(id=student_id)
        
        return Homework.objects.filter(
            class_assigned__class_level=student.current_class,
            class_assigned__stream=student.stream,
            due_date__gte=timezone.now().date()
        ).exclude(
            submissions__student_id=student_id
        ).select_related('subject', 'teacher').order_by('due_date')
    
    @staticmethod
    def get_overdue_homework():
        """Get overdue homework assignments"""
        return Homework.objects.filter(
            due_date__lt=timezone.now().date(),
            is_submitted=False
        ).select_related('subject', 'teacher', 'class_assigned')
    
    @staticmethod
    def calculate_submission_rate(homework_id):
        """Calculate submission rate for a homework"""
        homework = Homework.objects.get(id=homework_id)
        
        total_students = Student.objects.filter(
            current_class=homework.class_assigned.class_level,
            stream=homework.class_assigned.stream,
            is_active=True
        ).count()
        
        submissions = homework.submissions.count()
        
        return {
            'total_students': total_students,
            'submissions': submissions,
            'submission_rate': (submissions / total_students * 100) if total_students > 0 else 0,
        }

class ResultService:
    """Service for result operations"""
    
    @staticmethod
    def generate_report_card(student_id, term_id):
        """Generate report card for a student"""
        return ReportCardGenerator.generate_term_report(
            Student.objects.get(id=student_id),
            Term.objects.get(id=term_id)
        )
    
    @staticmethod
    def validate_marks(marks, subject_id):
        """Validate marks against subject's max mark"""
        subject = Subject.objects.get(id=subject_id)
        return 0 <= marks <= subject.max_mark
    
    @staticmethod
    def bulk_create_results(results_data, entered_by):
        """Bulk create results with validation"""
        created = []
        errors = []
        
        for data in results_data:
            try:
                # Validate
                if not ResultService.validate_marks(data['marks'], data['subject_id']):
                    errors.append(f"Invalid marks for {data['student_id']}")
                    continue
                
                # Create or update
                result, created_flag = Result.objects.update_or_create(
                    student_id=data['student_id'],
                    exam_id=data['exam_id'],
                    subject_id=data['subject_id'],
                    defaults={
                        'marks': data['marks'],
                        'remarks': data.get('remarks', ''),
                        'entered_by': entered_by,
                    }
                )
                
                if created_flag:
                    created.append(result)
                    
            except Exception as e:
                errors.append(str(e))
        
        return {
            'created': created,
            'errors': errors,
            'success_count': len(created),
            'error_count': len(errors),
        }
    
    @staticmethod
    def get_student_performance_trend(student_id, num_terms=3):
        """Get performance trend for a student"""
        return PerformanceAnalyzer.analyze_student_trend(
            Student.objects.get(id=student_id),
            num_terms
        )

class StatisticsService:
    """Service for academic statistics"""
    
    @staticmethod
    def get_school_performance_summary(term_id=None):
        """Get overall school performance summary"""
        if not term_id:
            term = Term.objects.filter(is_current=True).first()
            if not term:
                return None
            term_id = term.id
        
        # Overall statistics
        total_students = Student.objects.filter(is_active=True).count()
        students_with_results = ResultSummary.objects.filter(
            term_id=term_id
        ).count()
        
        # Class level performance
        class_performance = {}
        for class_level in range(1, 5):
            summaries = ResultSummary.objects.filter(
                term_id=term_id,
                student__current_class=class_level
            )
            
            if summaries.exists():
                avg = summaries.aggregate(Avg('average'))['average__avg']
                class_performance[class_level] = {
                    'average': avg,
                    'student_count': summaries.count(),
                    'top_student': summaries.order_by('-average').first(),
                }
        
        # Subject performance
        subject_performance = {}
        subjects = Subject.objects.filter(is_active=True)
        for subject in subjects:
            results = Result.objects.filter(
                exam__term_id=term_id,
                subject=subject
            )
            if results.exists():
                avg = results.aggregate(Avg('marks'))['marks__avg']
                subject_performance[subject.name] = avg
        
        return {
            'total_students': total_students,
            'students_with_results': students_with_results,
            'participation_rate': (students_with_results / total_students * 100) if total_students > 0 else 0,
            'class_performance': class_performance,
            'subject_performance': subject_performance,
        }
    
    @staticmethod
    def get_gender_performance_analysis(term_id):
        """Analyze performance by gender"""
        male_results = ResultSummary.objects.filter(
            term_id=term_id,
            student__gender='M'
        ).aggregate(
            avg=Avg('average'),
            count=Count('id')
        )
        
        female_results = ResultSummary.objects.filter(
            term_id=term_id,
            student__gender='F'
        ).aggregate(
            avg=Avg('average'),
            count=Count('id')
        )
        
        return {
            'male': {
                'average': male_results['avg'] or 0,
                'count': male_results['count'],
            },
            'female': {
                'average': female_results['avg'] or 0,
                'count': female_results['count'],
            },
            'gap': abs((male_results['avg'] or 0) - (female_results['avg'] or 0)),
        }
    
    @staticmethod
    def get_performance_distribution(term_id):
        """Get performance distribution across grade boundaries"""
        summaries = ResultSummary.objects.filter(term_id=term_id)
        
        distribution = {
            'A': 0, 'A-': 0, 'B+': 0, 'B': 0, 'B-': 0,
            'C+': 0, 'C': 0, 'C-': 0, 'D+': 0, 'D': 0, 'D-': 0, 'E': 0
        }
        
        for summary in summaries:
            if summary.mean_grade in distribution:
                distribution[summary.mean_grade] += 1
        
        return distribution