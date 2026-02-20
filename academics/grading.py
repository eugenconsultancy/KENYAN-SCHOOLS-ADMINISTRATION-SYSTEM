"""
Grading engine for Kenyan Schools System
Handles all grading calculations and conversions
"""

class GradingSystem:
    """Kenyan 8-4-4 and CBC grading system"""
    
    # Grade boundaries for 8-4-4 system
    GRADE_BOUNDARIES = [
        (80, 'A', 12),
        (75, 'A-', 11),
        (70, 'B+', 10),
        (65, 'B', 9),
        (60, 'B-', 8),
        (55, 'C+', 7),
        (50, 'C', 6),
        (45, 'C-', 5),
        (40, 'D+', 4),
        (35, 'D', 3),
        (30, 'D-', 2),
        (0, 'E', 1),
    ]
    
    @classmethod
    def get_grade_and_points(cls, marks):
        """Get grade and points from marks"""
        for boundary, grade, points in cls.GRADE_BOUNDARIES:
            if marks >= boundary:
                return grade, points
        return 'E', 1
    
    @classmethod
    def calculate_mean_grade(cls, points_list):
        """Calculate mean grade from list of points"""
        if not points_list:
            return 'E', 0
        
        total_points = sum(points_list)
        mean_points = total_points / len(points_list)
        
        # Convert mean points to grade
        for boundary, grade, points in cls.GRADE_BOUNDARIES:
            if mean_points >= points:
                return grade, mean_points
        
        return 'E', mean_points
    
    @classmethod
    def calculate_class_position(cls, students_results):
        """Calculate positions for students in a class"""
        # Sort students by total marks or average
        sorted_students = sorted(
            students_results.items(),
            key=lambda x: x[1]['average'],
            reverse=True
        )
        
        positions = {}
        current_position = 1
        previous_marks = None
        
        for i, (student_id, results) in enumerate(sorted_students, 1):
            if previous_marks is not None and results['average'] < previous_marks:
                current_position = i
            
            positions[student_id] = current_position
            previous_marks = results['average']
        
        return positions
    
    @classmethod
    def calculate_stream_positions(cls, stream_results):
        """Calculate positions within a stream"""
        positions = {}
        
        for stream, students in stream_results.items():
            positions[stream] = cls.calculate_class_position(students)
        
        return positions

class ReportCardGenerator:
    """Generate report card data"""
    
    @staticmethod
    def generate_term_report(student, term):
        """Generate comprehensive term report for a student"""
        from .models import Result, ResultSummary
        
        # Get all results for the student in this term
        results = Result.objects.filter(
            student=student,
            exam__term=term
        ).select_related('subject')
        
        if not results.exists():
            return None
        
        # Calculate subject performance
        subjects_data = []
        total_marks = 0
        total_points = 0
        
        for result in results:
            subjects_data.append({
                'subject': result.subject.name,
                'code': result.subject.code,
                'marks': result.marks,
                'grade': result.grade,
                'points': result.points,
                'remarks': result.remarks,
            })
            total_marks += result.marks
            total_points += result.points or 0
        
        # Get summary
        try:
            summary = ResultSummary.objects.get(student=student, term=term)
            average = summary.average
            mean_grade = summary.mean_grade
            position = summary.position_in_class
        except ResultSummary.DoesNotExist:
            average = total_marks / len(results) if results else 0
            mean_grade, _ = GradingSystem.get_grade_and_points(average)
            position = None
        
        return {
            'student': student,
            'term': term,
            'subjects': subjects_data,
            'total_marks': total_marks,
            'subjects_taken': len(subjects_data),
            'average': average,
            'mean_grade': mean_grade,
            'total_points': total_points,
            'position': position,
            'class': student.get_current_class_name(),
        }
    
    @staticmethod
    def generate_annual_report(student, academic_year):
        """Generate annual report across all terms"""
        from .models import Term, ResultSummary
        
        terms = Term.objects.filter(academic_year=academic_year).order_by('term')
        term_reports = []
        
        total_annual_marks = 0
        total_annual_points = 0
        terms_count = 0
        
        for term in terms:
            report = ReportCardGenerator.generate_term_report(student, term)
            if report:
                term_reports.append(report)
                total_annual_marks += report['total_marks']
                total_annual_points += report['total_points']
                terms_count += 1
        
        if terms_count == 0:
            return None
        
        annual_average = total_annual_marks / (terms_count * (report['subjects_taken'] or 1))
        annual_mean_grade, _ = GradingSystem.get_grade_and_points(annual_average)
        
        return {
            'student': student,
            'academic_year': academic_year,
            'term_reports': term_reports,
            'annual_average': annual_average,
            'annual_mean_grade': annual_mean_grade,
            'annual_total_points': total_annual_points,
        }

class RankCalculator:
    """Calculate rankings for students"""
    
    @staticmethod
    def calculate_class_rankings(class_obj, term):
        """Calculate rankings for all students in a class"""
        from .models import Student, Result
        
        students = Student.objects.filter(
            current_class=class_obj.class_level,
            stream=class_obj.stream,
            is_active=True
        )
        
        rankings = []
        for student in students:
            results = Result.objects.filter(
                student=student,
                exam__term=term
            )
            
            if results.exists():
                total = sum(r.marks for r in results)
                average = total / len(results)
                rankings.append({
                    'student': student,
                    'total': total,
                    'average': average,
                    'subjects': len(results),
                })
        
        # Sort by average
        rankings.sort(key=lambda x: x['average'], reverse=True)
        
        # Assign positions
        for i, rank in enumerate(rankings, 1):
            rank['position'] = i
        
        return rankings
    
    @staticmethod
    def calculate_stream_rankings(class_level, term):
        """Calculate rankings across all streams in a class level"""
        from .models import Class
        
        streams = Class.objects.filter(
            class_level=class_level,
            academic_year=term.academic_year
        )
        
        stream_rankings = {}
        for stream in streams:
            stream_rankings[stream.stream] = RankCalculator.calculate_class_rankings(stream, term)
        
        return stream_rankings
    
    @staticmethod
    def calculate_overall_rankings(term):
        """Calculate overall school rankings"""
        from .models import Class
        
        all_rankings = {}
        for class_level in range(1, 5):
            all_rankings[class_level] = RankCalculator.calculate_stream_rankings(class_level, term)
        
        return all_rankings