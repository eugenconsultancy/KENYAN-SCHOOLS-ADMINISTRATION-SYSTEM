"""
Ranking engine for Kenyan Schools System
Handles student ranking calculations
"""

from django.db.models import Avg, Sum, Count, Q
from .models import Result, ResultSummary, Class, Term
from students.models import Student
from .grading import GradingSystem

class RankingService:
    """Service for calculating student rankings"""
    
    @staticmethod
    def update_term_summaries(term):
        """Update result summaries for all students in a term"""
        from students.models import Student
        
        students = Student.objects.filter(is_active=True)
        
        for student in students:
            RankingService.update_student_term_summary(student, term)
    
    @staticmethod
    def update_student_term_summary(student, term):
        """Update result summary for a single student"""
        from .models import Result, ResultSummary
        
        results = Result.objects.filter(student=student, exam__term=term)
        
        if not results.exists():
            return None
        
        total_marks = sum(r.marks for r in results)
        subjects_count = results.count()
        average = total_marks / subjects_count
        
        # Calculate total points
        total_points = sum(r.points or 0 for r in results)
        
        # Calculate mean grade
        points_list = [r.points or 0 for r in results]
        mean_grade, _ = GradingSystem.calculate_mean_grade(points_list)
        
        # Get or create summary
        summary, created = ResultSummary.objects.update_or_create(
            student=student,
            term=term,
            defaults={
                'total_marks': total_marks,
                'average': average,
                'mean_grade': mean_grade,
                'total_points': total_points,
                'subjects_taken': subjects_count,
            }
        )
        
        return summary
    
    @staticmethod
    def calculate_class_positions(term, class_level=None, stream=None):
        """Calculate positions for all students in a class"""
        from students.models import Student
        
        # Get all students in the class
        students = Student.objects.filter(is_active=True)
        if class_level:
            students = students.filter(current_class=class_level)
        if stream:
            students = students.filter(stream=stream)
        
        # Get their summaries
        summaries = ResultSummary.objects.filter(
            student__in=students,
            term=term
        ).select_related('student')
        
        # Sort by average (descending)
        sorted_summaries = sorted(summaries, key=lambda x: x.average, reverse=True)
        
        # Assign positions
        positions = {}
        current_position = 1
        previous_avg = None
        
        for i, summary in enumerate(sorted_summaries, 1):
            if previous_avg is not None and summary.average < previous_avg:
                current_position = i
            
            # Update position in database
            summary.position_in_class = current_position
            summary.save()
            
            positions[summary.student.id] = current_position
            previous_avg = summary.average
        
        return positions
    
    @staticmethod
    def calculate_stream_positions(term, class_level):
        """Calculate positions within streams for a class level"""
        from students.models import Student
        
        streams = ['East', 'West', 'North', 'South']
        stream_positions = {}
        
        for stream in streams:
            students = Student.objects.filter(
                current_class=class_level,
                stream=stream,
                is_active=True
            )
            
            summaries = ResultSummary.objects.filter(
                student__in=students,
                term=term
            ).select_related('student')
            
            # Sort by average
            sorted_summaries = sorted(summaries, key=lambda x: x.average, reverse=True)
            
            # Assign stream positions
            for i, summary in enumerate(sorted_summaries, 1):
                summary.position_in_stream = i
                summary.save()
            
            stream_positions[stream] = len(sorted_summaries)
        
        return stream_positions
    
    @staticmethod
    def calculate_overall_positions(term):
        """Calculate overall positions for all classes"""
        positions = {}
        
        for class_level in range(1, 5):
            positions[class_level] = {
                'class': RankingService.calculate_class_positions(term, class_level),
                'streams': RankingService.calculate_stream_positions(term, class_level),
            }
        
        return positions
    
    @staticmethod
    def get_top_performers(term, class_level=None, limit=10):
        """Get top performing students"""
        summaries = ResultSummary.objects.filter(term=term)
        
        if class_level:
            summaries = summaries.filter(student__current_class=class_level)
        
        return summaries.select_related('student').order_by('-average')[:limit]
    
    @staticmethod
    def get_subject_ranking(subject, term, class_level=None):
        """Get ranking for a specific subject"""
        from students.models import Student
        
        results = Result.objects.filter(
            exam__term=term,
            subject=subject
        ).select_related('student')
        
        if class_level:
            results = results.filter(student__current_class=class_level)
        
        # Group by student and get their marks
        student_marks = {}
        for result in results:
            student_marks[result.student.id] = {
                'student': result.student,
                'marks': result.marks,
                'grade': result.grade,
            }
        
        # Sort by marks
        sorted_students = sorted(
            student_marks.values(),
            key=lambda x: x['marks'],
            reverse=True
        )
        
        # Assign positions
        for i, student in enumerate(sorted_students, 1):
            student['position'] = i
        
        return sorted_students
    
    @staticmethod
    def get_class_mean_score(term, class_level, stream=None):
        """Calculate mean score for a class"""
        from students.models import Student
        
        summaries = ResultSummary.objects.filter(
            term=term,
            student__current_class=class_level
        )
        
        if stream:
            summaries = summaries.filter(student__stream=stream)
        
        if not summaries.exists():
            return 0
        
        total_average = sum(s.average for s in summaries)
        return total_average / summaries.count()

class PerformanceAnalyzer:
    """Analyze student performance trends"""
    
    @staticmethod
    def analyze_student_trend(student, num_terms=3):
        """Analyze performance trend for a student over multiple terms"""
        summaries = ResultSummary.objects.filter(
            student=student
        ).select_related('term__academic_year').order_by('-term__academic_year', '-term__term')[:num_terms]
        
        if not summaries.exists():
            return None
        
        trend_data = []
        for summary in summaries:
            trend_data.append({
                'term': str(summary.term),
                'average': float(summary.average),
                'mean_grade': summary.mean_grade,
                'position': summary.position_in_class,
            })
        
        # Calculate improvement
        if len(trend_data) >= 2:
            improvement = trend_data[0]['average'] - trend_data[-1]['average']
        else:
            improvement = 0
        
        return {
            'trend': trend_data,
            'improvement': improvement,
            'best_term': max(trend_data, key=lambda x: x['average']),
            'worst_term': min(trend_data, key=lambda x: x['average']),
        }
    
    @staticmethod
    def analyze_class_performance(term, class_level):
        """Analyze performance for an entire class"""
        from students.models import Student
        
        summaries = ResultSummary.objects.filter(
            term=term,
            student__current_class=class_level
        ).select_related('student')
        
        if not summaries.exists():
            return None
        
        averages = [s.average for s in summaries]
        
        # Calculate statistics
        mean_score = sum(averages) / len(averages)
        max_score = max(averages)
        min_score = min(averages)
        
        # Grade distribution
        grade_distribution = {}
        for summary in summaries:
            grade = summary.mean_grade
            grade_distribution[grade] = grade_distribution.get(grade, 0) + 1
        
        # Performance categories
        excellent = sum(1 for s in summaries if s.average >= 80)
        good = sum(1 for s in summaries if 70 <= s.average < 80)
        fair = sum(1 for s in summaries if 50 <= s.average < 70)
        poor = sum(1 for s in summaries if s.average < 50)
        
        return {
            'total_students': len(summaries),
            'mean_score': mean_score,
            'max_score': max_score,
            'min_score': min_score,
            'grade_distribution': grade_distribution,
            'excellent': excellent,
            'good': good,
            'fair': fair,
            'poor': poor,
            'excellent_percentage': (excellent / len(summaries)) * 100,
        }
    
    @staticmethod
    def compare_streams(term, class_level):
        """Compare performance across streams"""
        from students.models import Student
        
        streams = ['East', 'West', 'North', 'South']
        stream_performance = {}
        
        for stream in streams:
            summaries = ResultSummary.objects.filter(
                term=term,
                student__current_class=class_level,
                student__stream=stream
            )
            
            if summaries.exists():
                avg = sum(s.average for s in summaries) / len(summaries)
                stream_performance[stream] = {
                    'average': avg,
                    'count': len(summaries),
                    'top_student': summaries.order_by('-average').first(),
                }
        
        return stream_performance
    
    @staticmethod
    def subject_performance_analysis(term, class_level=None):
        """Analyze performance by subject"""
        from .models import Subject
        from students.models import Student
        
        subjects = Subject.objects.filter(is_active=True)
        analysis = {}
        
        for subject in subjects:
            results = Result.objects.filter(
                exam__term=term,
                subject=subject
            )
            
            if class_level:
                results = results.filter(student__current_class=class_level)
            
            if results.exists():
                marks = [r.marks for r in results]
                analysis[subject.name] = {
                    'mean': sum(marks) / len(marks),
                    'max': max(marks),
                    'min': min(marks),
                    'pass_rate': sum(1 for m in marks if m >= 50) / len(marks) * 100,
                    'total_students': len(marks),
                }
        
        return analysis