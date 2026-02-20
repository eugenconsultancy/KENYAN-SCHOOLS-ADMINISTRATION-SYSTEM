"""
Result Reports Module
Handles generation of academic results and report cards
"""

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from django.utils import timezone
from django.db.models import Avg, Sum, Count
from .report_generator import ReportGenerator
from academics.models import Result, ResultSummary, Exam, Term, Subject
from students.models import Student
from teachers.models import Teacher
import datetime

class ResultReportGenerator(ReportGenerator):
    """Generator for academic results reports"""
    
    @staticmethod
    def generate_student_term_report(student, term):
        """Generate report card for a student for a specific term"""
        
        generator = ReportGenerator(f"Report Card: {student.get_full_name()}")
        generator.add_header_info(
            Term=f"{term}",
            Class=student.get_current_class_name(),
            Admission=student.admission_number
        )
        
        # Get results for this term
        results = Result.objects.filter(
            student=student,
            exam__term=term
        ).select_related('subject', 'exam').order_by('subject__name')
        
        if not results.exists():
            generator.add_paragraph("No results available for this term.")
            return generator.generate()
        
        # Student Information
        generator.add_subtitle("Student Information")
        info_data = [
            ['Name', student.get_full_name()],
            ['Admission No.', student.admission_number],
            ['Class', student.get_current_class_name()],
            ['Term', str(term)],
        ]
        generator.add_table(info_data, col_widths=[2*inch, 4*inch])
        
        # Subject Results
        generator.add_subtitle("Subject Performance")
        
        results_data = [['Subject', 'Marks', 'Grade', 'Points', 'Remarks']]
        total_marks = 0
        total_points = 0
        
        for result in results:
            results_data.append([
                result.subject.name,
                str(result.marks),
                result.grade,
                str(result.points) if result.points else '-',
                result.remarks or '-'
            ])
            total_marks += result.marks
            total_points += result.points or 0
        
        generator.add_table(results_data, col_widths=[2*inch, 0.8*inch, 0.8*inch, 0.8*inch, 1.8*inch])
        
        # Summary
        generator.add_subtitle("Performance Summary")
        
        subjects_count = results.count()
        average = total_marks / subjects_count if subjects_count > 0 else 0
        
        # Get summary if exists
        try:
            summary = ResultSummary.objects.get(student=student, term=term)
            mean_grade = summary.mean_grade
            position = summary.position_in_class
        except ResultSummary.DoesNotExist:
            mean_grade = Result.calculate_grade(average)
            position = 'N/A'
        
        summary_data = [
            ['Total Subjects', str(subjects_count)],
            ['Total Marks', str(total_marks)],
            ['Average Score', f"{average:.1f}"],
            ['Mean Grade', mean_grade],
            ['Total Points', str(total_points)],
            ['Class Position', str(position) if position else 'N/A'],
        ]
        
        generator.add_table(summary_data, col_widths=[2.5*inch, 2.5*inch])
        
        # Grading Scale
        generator.add_subtitle("Grading Scale")
        scale_data = [
            ['Grade', 'Marks Range', 'Points'],
            ['A', '80 - 100', '12'],
            ['A-', '75 - 79', '11'],
            ['B+', '70 - 74', '10'],
            ['B', '65 - 69', '9'],
            ['B-', '60 - 64', '8'],
            ['C+', '55 - 59', '7'],
            ['C', '50 - 54', '6'],
            ['C-', '45 - 49', '5'],
            ['D+', '40 - 44', '4'],
            ['D', '35 - 39', '3'],
            ['D-', '30 - 34', '2'],
            ['E', '0 - 29', '1'],
        ]
        
        generator.add_table(scale_data, col_widths=[1*inch, 2*inch, 1*inch])
        
        # Teacher's Comments
        generator.add_subtitle("Teacher's Comments")
        generator.add_paragraph("_______________________________________________________________________________")
        generator.add_paragraph("_______________________________________________________________________________")
        
        # Principal's Remarks
        generator.add_subtitle("Principal's Remarks")
        generator.add_paragraph("_______________________________________________________________________________")
        generator.add_paragraph("_______________________________________________________________________________")
        
        generator.add_signature_block()
        
        return generator.generate()
    
    @staticmethod
    def generate_class_result_slips(class_obj, exam):
        """Generate result slips for all students in a class"""
        
        generator = ReportGenerator(f"Result Slips - {class_obj} - {exam}")
        generator.add_header_info()
        
        # Get students in this class
        students = Student.objects.filter(
            current_class=class_obj.class_level,
            stream=class_obj.stream,
            is_active=True
        ).order_by('user__first_name')
        
        for student in students:
            # Get results for this exam
            results = Result.objects.filter(
                student=student,
                exam=exam
            ).select_related('subject').order_by('subject__name')
            
            if not results.exists():
                continue
            
            # Student Result Slip
            generator.add_subtitle(f"Report Card: {student.get_full_name()}")
            generator.add_paragraph(f"Admission No: {student.admission_number}")
            generator.add_paragraph(f"Class: {student.get_current_class_name()}")
            generator.add_paragraph("")
            
            # Results Table
            data = [['Subject', 'Marks', 'Grade']]
            total_marks = 0
            
            for result in results:
                data.append([
                    result.subject.name,
                    str(result.marks),
                    result.grade
                ])
                total_marks += result.marks
            
            # Add summary row
            subjects_count = len(results)
            average = total_marks / subjects_count if subjects_count > 0 else 0
            data.append(['', '', ''])
            data.append(['Total', str(total_marks), ''])
            data.append(['Average', f"{average:.1f}", Result.calculate_grade(average)])
            
            generator.add_table(data, col_widths=[3*inch, 1*inch, 1*inch])
            
            # Add signature lines
            generator.add_paragraph("")
            generator.add_paragraph("Class Teacher: ____________________  Date: _______________")
            generator.add_paragraph("Principal: ________________________  Date: _______________")
            
            # Add page break between students (except last)
            if student != students.last():
                generator.add_page_break()
        
        return generator.generate()
    
    @staticmethod
    def generate_term_report(term, class_level=None, stream=None):
        """Generate comprehensive term report"""
        
        title = f"Term Report - {term}"
        if class_level:
            title += f" - Form {class_level}"
            if stream:
                title += f" {stream}"
        
        generator = ReportGenerator(title)
        generator.add_header_info()
        
        # Get students
        students = Student.objects.filter(is_active=True)
        if class_level:
            students = students.filter(current_class=class_level)
        if stream:
            students = students.filter(stream=stream)
        
        # Get all results for this term
        results = Result.objects.filter(
            student__in=students,
            exam__term=term
        ).select_related('student', 'subject')
        
        if not results.exists():
            generator.add_paragraph("No results available for this term.")
            return generator.generate()
        
        # Overall Statistics
        generator.add_subtitle("Overall Performance Statistics")
        
        total_students = students.count()
        students_with_results = results.values('student').distinct().count()
        total_subjects = results.values('subject').distinct().count()
        total_exams = Exam.objects.filter(term=term).count()
        
        stats_data = [
            ['Total Students', str(total_students)],
            ['Students with Results', str(students_with_results)],
            ['Participation Rate', f"{(students_with_results/total_students*100):.1f}%" if total_students > 0 else '0%'],
            ['Total Subjects', str(total_subjects)],
            ['Total Exams', str(total_exams)],
        ]
        
        generator.add_table(stats_data, col_widths=[3*inch, 3*inch])
        
        # Subject Performance
        generator.add_subtitle("Subject Performance Analysis")
        
        subject_stats = []
        for subject in Subject.objects.filter(is_active=True):
            subject_results = results.filter(subject=subject)
            if subject_results.exists():
                avg = subject_results.aggregate(Avg('marks'))['marks__avg']
                max_mark = subject_results.aggregate(Avg('marks'))['marks__max'] if hasattr(subject_results, 'max') else 0
                min_mark = subject_results.aggregate(Avg('marks'))['marks__min'] if hasattr(subject_results, 'min') else 0
                pass_count = subject_results.filter(marks__gte=50).count()
                total_count = subject_results.count()
                pass_rate = (pass_count / total_count * 100) if total_count > 0 else 0
                
                subject_stats.append({
                    'name': subject.name,
                    'avg': avg,
                    'max': max_mark,
                    'min': min_mark,
                    'pass_rate': pass_rate,
                    'students': total_count
                })
        
        # Sort by average
        subject_stats.sort(key=lambda x: x['avg'], reverse=True)
        
        subject_data = [['Subject', 'Average', 'Max', 'Min', 'Pass Rate', 'Students']]
        for stat in subject_stats:
            subject_data.append([
                stat['name'],
                f"{stat['avg']:.1f}",
                f"{stat['max']:.1f}",
                f"{stat['min']:.1f}",
                f"{stat['pass_rate']:.1f}%",
                str(stat['students'])
            ])
        
        generator.add_table(subject_data, col_widths=[2*inch, 0.8*inch, 0.8*inch, 0.8*inch, 1*inch, 0.8*inch])
        
        # Class Performance
        if not class_level:
            generator.add_page_break()
            generator.add_subtitle("Class Performance Comparison")
            
            class_data = [['Class', 'Average', 'Students', 'Top Student']]
            
            for level in range(1, 5):
                for strm in ['East', 'West', 'North', 'South']:
                    class_students = Student.objects.filter(
                        current_class=level,
                        stream=strm,
                        is_active=True
                    )
                    
                    if class_students.exists():
                        class_results = results.filter(student__in=class_students)
                        if class_results.exists():
                            class_avg = class_results.aggregate(Avg('marks'))['marks__avg']
                            
                            # Get top student
                            student_averages = {}
                            for student in class_students:
                                student_results = class_results.filter(student=student)
                                if student_results.exists():
                                    student_avg = student_results.aggregate(Avg('marks'))['marks__avg']
                                    student_averages[student.get_full_name()] = student_avg
                            
                            top_student = max(student_averages, key=student_averages.get) if student_averages else 'N/A'
                            
                            class_data.append([
                                f"Form {level} {strm}",
                                f"{class_avg:.1f}",
                                str(class_students.count()),
                                top_student
                            ])
            
            generator.add_table(class_data, col_widths=[1.5*inch, 1*inch, 1*inch, 2.5*inch])
        
        # Top Performers
        generator.add_page_break()
        generator.add_subtitle("Top 10 Students Overall")
        
        # Calculate student averages
        student_averages = {}
        for student in students:
            student_results = results.filter(student=student)
            if student_results.exists():
                avg = student_results.aggregate(Avg('marks'))['marks__avg']
                student_averages[student] = avg
        
        # Sort and get top 10
        top_students = sorted(student_averages.items(), key=lambda x: x[1], reverse=True)[:10]
        
        top_data = [['#', 'Admission No.', 'Student Name', 'Class', 'Average', 'Grade']]
        for i, (student, avg) in enumerate(top_students, 1):
            top_data.append([
                str(i),
                student.admission_number,
                student.get_full_name(),
                student.get_current_class_name(),
                f"{avg:.1f}",
                Result.calculate_grade(avg)
            ])
        
        generator.add_table(top_data, col_widths=[0.4*inch, 1*inch, 1.8*inch, 1*inch, 1*inch, 0.8*inch])
        
        generator.add_signature_block()
        
        return generator.generate()
    
    @staticmethod
    def generate_exam_performance_report(exam):
        """Generate detailed exam performance report"""
        
        generator = ReportGenerator(f"Exam Performance Report: {exam.name}")
        generator.add_header_info(
            Term=str(exam.term),
            Type=exam.get_exam_type_display()
        )
        
        # Get all results for this exam
        results = Result.objects.filter(exam=exam).select_related('student', 'subject')
        
        if not results.exists():
            generator.add_paragraph("No results available for this exam.")
            return generator.generate()
        
        # Overall Statistics
        generator.add_subtitle("Overall Statistics")
        
        total_students = results.values('student').distinct().count()
        total_subjects = results.values('subject').distinct().count()
        total_marks = results.aggregate(Sum('marks'))['marks__sum'] or 0
        overall_avg = results.aggregate(Avg('marks'))['marks__avg'] or 0
        
        stats_data = [
            ['Total Students', str(total_students)],
            ['Total Subjects', str(total_subjects)],
            ['Total Marks', f"{total_marks:.1f}"],
            ['Overall Average', f"{overall_avg:.1f}"],
        ]
        
        generator.add_table(stats_data, col_widths=[3*inch, 3*inch])
        
        # Subject-wise Performance
        generator.add_subtitle("Subject Performance")
        
        subject_data = [['Subject', 'Students', 'Average', 'Highest', 'Lowest', 'Pass Rate']]
        
        subjects = Subject.objects.filter(id__in=results.values_list('subject', flat=True).distinct())
        for subject in subjects:
            subject_results = results.filter(subject=subject)
            avg = subject_results.aggregate(Avg('marks'))['marks__avg']
            highest = subject_results.order_by('-marks').first()
            lowest = subject_results.order_by('marks').first()
            pass_count = subject_results.filter(marks__gte=50).count()
            total_count = subject_results.count()
            pass_rate = (pass_count / total_count * 100) if total_count > 0 else 0
            
            subject_data.append([
                subject.name,
                str(total_count),
                f"{avg:.1f}",
                f"{highest.marks} ({highest.student.get_full_name()})" if highest else '-',
                f"{lowest.marks} ({lowest.student.get_full_name()})" if lowest else '-',
                f"{pass_rate:.1f}%"
            ])
        
        generator.add_table(subject_data, colWidths=[1.5*inch, 0.8*inch, 0.8*inch, 2*inch, 2*inch, 0.8*inch])
        
        # Grade Distribution
        generator.add_page_break()
        generator.add_subtitle("Grade Distribution")
        
        grade_counts = {
            'A': 0, 'A-': 0, 'B+': 0, 'B': 0, 'B-': 0,
            'C+': 0, 'C': 0, 'C-': 0, 'D+': 0, 'D': 0, 'D-': 0, 'E': 0
        }
        
        for result in results:
            grade_counts[result.grade] = grade_counts.get(result.grade, 0) + 1
        
        grade_data = [['Grade', 'Count', 'Percentage']]
        total_results = results.count()
        
        for grade in ['A', 'A-', 'B+', 'B', 'B-', 'C+', 'C', 'C-', 'D+', 'D', 'D-', 'E']:
            count = grade_counts.get(grade, 0)
            percentage = (count / total_results * 100) if total_results > 0 else 0
            grade_data.append([grade, str(count), f"{percentage:.1f}%"])
        
        generator.add_table(grade_data, col_widths=[1*inch, 2*inch, 2*inch])
        
        # Top Performers
        generator.add_subtitle("Top 10 Students")
        
        # Calculate student totals
        student_totals = {}
        for student_id in results.values_list('student', flat=True).distinct():
            student_results = results.filter(student_id=student_id)
            total = student_results.aggregate(Sum('marks'))['marks__sum'] or 0
            student = Student.objects.get(id=student_id)
            student_totals[student] = total
        
        top_students = sorted(student_totals.items(), key=lambda x: x[1], reverse=True)[:10]
        
        top_data = [['#', 'Admission No.', 'Student Name', 'Class', 'Total Marks']]
        for i, (student, total) in enumerate(top_students, 1):
            top_data.append([
                str(i),
                student.admission_number,
                student.get_full_name(),
                student.get_current_class_name(),
                f"{total:.1f}"
            ])
        
        generator.add_table(top_data, col_widths=[0.4*inch, 1*inch, 1.8*inch, 1*inch, 1*inch])
        
        generator.add_signature_block()
        
        return generator.generate()
    
    @staticmethod
    def generate_ranking_report(term, class_level=None):
        """Generate ranking report"""
        
        title = f"Ranking Report - {term}"
        if class_level:
            title += f" - Form {class_level}"
        
        generator = ReportGenerator(title)
        generator.add_header_info()
        
        # Get summaries
        summaries = ResultSummary.objects.filter(term=term).select_related('student')
        if class_level:
            summaries = summaries.filter(student__current_class=class_level)
        
        summaries = summaries.order_by('-average')
        
        if not summaries.exists():
            generator.add_paragraph("No ranking data available for this term.")
            return generator.generate()
        
        # Overall Rankings
        generator.add_subtitle("Overall Student Rankings")
        
        rank_data = [['Rank', 'Admission No.', 'Student Name', 'Class', 'Average', 'Grade', 'Points']]
        for i, summary in enumerate(summaries, 1):
            rank_data.append([
                str(i),
                summary.student.admission_number,
                summary.student.get_full_name(),
                summary.student.get_current_class_name(),
                f"{summary.average:.1f}",
                summary.mean_grade,
                str(summary.total_points)
            ])
        
        generator.add_table(rank_data, col_widths=[0.5*inch, 1*inch, 1.8*inch, 1*inch, 0.8*inch, 0.8*inch, 0.8*inch])
        
        # Class-wise Rankings
        if not class_level:
            generator.add_page_break()
            generator.add_subtitle("Class-wise Rankings")
            
            for level in range(1, 5):
                for stream in ['East', 'West', 'North', 'South']:
                    class_summaries = summaries.filter(
                        student__current_class=level,
                        student__stream=stream
                    ).order_by('-average')
                    
                    if class_summaries.exists():
                        generator.add_subtitle(f"Form {level} {stream}")
                        
                        class_data = [['Rank', 'Admission No.', 'Student Name', 'Average', 'Grade']]
                        for j, summary in enumerate(class_summaries, 1):
                            class_data.append([
                                str(j),
                                summary.student.admission_number,
                                summary.student.get_full_name(),
                                f"{summary.average:.1f}",
                                summary.mean_grade
                            ])
                        
                        generator.add_table(class_data, col_widths=[0.5*inch, 1.2*inch, 2*inch, 1*inch, 0.8*inch])
                        generator.add_paragraph("")
        
        generator.add_signature_block()
        
        return generator.generate()