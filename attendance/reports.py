"""
Attendance Reports Module
Handles generation of attendance reports using the reports framework
"""

from django.db.models import Count, Q, Sum, Avg
from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from .models import Attendance, TeacherAttendance, AttendanceSummary, Holiday
from students.models import Student
from teachers.models import Teacher
from academics.models import Term
import datetime
import calendar

class AttendanceReportGenerator:
    """Generator for attendance reports"""
    
    @staticmethod
    def generate_daily_report(date, class_level=None, stream=None):
        """Generate daily attendance report"""
        
        from reports.report_generator import ReportGenerator
        
        title = f"Daily Attendance Report - {date}"
        if class_level:
            title += f" - Form {class_level}"
            if stream:
                title += f" {stream}"
        
        generator = ReportGenerator(title)
        generator.add_header_info(Date=date)
        
        # Get attendance records
        attendance = Attendance.objects.filter(date=date)
        
        if class_level:
            attendance = attendance.filter(class_level=class_level)
        if stream:
            attendance = attendance.filter(stream=stream)
        
        # Overall Statistics
        generator.add_subtitle("Summary")
        
        total_students = attendance.count()
        present = attendance.filter(status='present').count()
        absent = attendance.filter(status='absent').count()
        late = attendance.filter(status='late').count()
        excused = attendance.filter(status__in=['excused', 'sick', 'sports', 'official']).count()
        
        stats_data = [
            ['Metric', 'Count', 'Percentage'],
            ['Total Students', str(total_students), '100%'],
            ['Present', str(present), f"{(present/total_students*100):.1f}%" if total_students > 0 else '0%'],
            ['Absent', str(absent), f"{(absent/total_students*100):.1f}%" if total_students > 0 else '0%'],
            ['Late', str(late), f"{(late/total_students*100):.1f}%" if total_students > 0 else '0%'],
            ['Excused', str(excused), f"{(excused/total_students*100):.1f}%" if total_students > 0 else '0%'],
        ]
        
        generator.add_table(stats_data, col_widths=[2*inch, 1.5*inch, 1.5*inch])
        
        # Class-wise Breakdown
        if not class_level:
            generator.add_subtitle("Class-wise Attendance")
            
            class_data = [['Class', 'Total', 'Present', 'Absent', 'Late', 'Rate']]
            
            for level in range(1, 5):
                for strm in ['East', 'West', 'North', 'South']:
                    class_attendance = attendance.filter(class_level=level, stream=strm)
                    if class_attendance.exists():
                        class_total = class_attendance.count()
                        class_present = class_attendance.filter(status='present').count()
                        class_absent = class_attendance.filter(status='absent').count()
                        class_late = class_attendance.filter(status='late').count()
                        rate = (class_present / class_total * 100) if class_total > 0 else 0
                        
                        class_data.append([
                            f"Form {level} {strm}",
                            str(class_total),
                            str(class_present),
                            str(class_absent),
                            str(class_late),
                            f"{rate:.1f}%"
                        ])
            
            generator.add_table(class_data, col_widths=[1.5*inch, 0.8*inch, 0.8*inch, 0.8*inch, 0.8*inch, 0.8*inch])
        
        # Detailed List
        generator.add_page_break()
        generator.add_subtitle("Detailed Attendance List")
        
        detail_data = [['#', 'Admission No.', 'Student Name', 'Class', 'Status', 'Time', 'Reason']]
        
        for i, record in enumerate(attendance.order_by('class_level', 'stream', 'student__user__first_name'), 1):
            check_time = record.check_in_time.strftime('%H:%M') if record.check_in_time else '-'
            
            detail_data.append([
                str(i),
                record.student.admission_number,
                record.student.get_full_name(),
                f"F{record.class_level}{record.stream}",
                record.get_status_display(),
                check_time,
                record.reason[:30] + ('...' if len(record.reason) > 30 else '') if record.reason else '-'
            ])
        
        generator.add_table(detail_data, col_widths=[0.4*inch, 1*inch, 1.8*inch, 0.8*inch, 0.8*inch, 0.8*inch, 1.5*inch])
        
        generator.add_signature_block()
        
        return generator.generate()
    
    @staticmethod
    def generate_weekly_report(start_date, end_date):
        """Generate weekly attendance report"""
        
        from reports.report_generator import ReportGenerator
        
        generator = ReportGenerator(f"Weekly Attendance Report: {start_date} to {end_date}")
        generator.add_header_info()
        
        # Get attendance for the week
        attendance = Attendance.objects.filter(
            date__gte=start_date,
            date__lte=end_date
        )
        
        if not attendance.exists():
            generator.add_paragraph("No attendance records for this period.")
            return generator.generate()
        
        # Weekly Summary
        generator.add_subtitle("Weekly Summary")
        
        total_records = attendance.count()
        present = attendance.filter(status='present').count()
        absent = attendance.filter(status='absent').count()
        late = attendance.filter(status='late').count()
        
        avg_daily = total_records / 7 if total_records > 0 else 0
        
        summary_data = [
            ['Total Attendance Records', str(total_records)],
            ['Average Daily Attendance', f"{avg_daily:.1f}"],
            ['Total Present', str(present)],
            ['Total Absent', str(absent)],
            ['Total Late', str(late)],
            ['Overall Attendance Rate', f"{(present/total_records*100):.1f}%" if total_records > 0 else '0%'],
        ]
        
        generator.add_table(summary_data, col_widths=[3*inch, 3*inch])
        
        # Daily Breakdown
        generator.add_subtitle("Daily Attendance")
        
        daily_data = [['Date', 'Day', 'Present', 'Absent', 'Late', 'Total', 'Rate']]
        
        current = start_date
        while current <= end_date:
            day_attendance = attendance.filter(date=current)
            if day_attendance.exists():
                day_present = day_attendance.filter(status='present').count()
                day_absent = day_attendance.filter(status='absent').count()
                day_late = day_attendance.filter(status='late').count()
                day_total = day_attendance.count()
                day_rate = (day_present / day_total * 100) if day_total > 0 else 0
                
                daily_data.append([
                    current.strftime('%Y-%m-%d'),
                    current.strftime('%A'),
                    str(day_present),
                    str(day_absent),
                    str(day_late),
                    str(day_total),
                    f"{day_rate:.1f}%"
                ])
            current += datetime.timedelta(days=1)
        
        generator.add_table(daily_data, col_widths=[1*inch, 1*inch, 0.8*inch, 0.8*inch, 0.8*inch, 0.8*inch, 0.8*inch])
        
        # Top/Bottom Performers
        generator.add_page_break()
        generator.add_subtitle("Student Attendance Summary")
        
        # Get all students
        students = Student.objects.filter(is_active=True)
        student_stats = []
        
        for student in students:
            student_attendance = attendance.filter(student=student)
            if student_attendance.exists():
                student_present = student_attendance.filter(status='present').count()
                student_total = student_attendance.count()
                student_rate = (student_present / student_total * 100)
                student_stats.append({
                    'name': student.get_full_name(),
                    'admission': student.admission_number,
                    'class': student.get_current_class_name(),
                    'present': student_present,
                    'total': student_total,
                    'rate': student_rate
                })
        
        # Sort by attendance rate
        student_stats.sort(key=lambda x: x['rate'], reverse=True)
        
        # Top 10
        generator.add_subtitle("Top 10 Students")
        top_data = [['#', 'Admission', 'Name', 'Class', 'Present/Total', 'Rate']]
        for i, stat in enumerate(student_stats[:10], 1):
            top_data.append([
                str(i),
                stat['admission'],
                stat['name'],
                stat['class'],
                f"{stat['present']}/{stat['total']}",
                f"{stat['rate']:.1f}%"
            ])
        generator.add_table(top_data, col_widths=[0.4*inch, 1*inch, 1.5*inch, 1*inch, 1*inch, 0.8*inch])
        
        # Bottom 10
        generator.add_subtitle("Bottom 10 Students")
        bottom_data = [['#', 'Admission', 'Name', 'Class', 'Present/Total', 'Rate']]
        for i, stat in enumerate(reversed(student_stats[-10:]), 1):
            bottom_data.append([
                str(i),
                stat['admission'],
                stat['name'],
                stat['class'],
                f"{stat['present']}/{stat['total']}",
                f"{stat['rate']:.1f}%"
            ])
        generator.add_table(bottom_data, col_widths=[0.4*inch, 1*inch, 1.5*inch, 1*inch, 1*inch, 0.8*inch])
        
        generator.add_signature_block()
        
        return generator.generate()
    
    @staticmethod
    def generate_monthly_summary_report(year, month):
        """Generate monthly attendance summary report"""
        
        from reports.report_generator import ReportGenerator
        
        month_name = calendar.month_name[int(month)]
        generator = ReportGenerator(f"Monthly Attendance Summary - {month_name} {year}")
        generator.add_header_info()
        
        # Get summaries
        summaries = AttendanceSummary.objects.filter(year=year, month=month).select_related('student')
        
        if not summaries.exists():
            generator.add_paragraph("No attendance summaries available for this month.")
            return generator.generate()
        
        # Overall Statistics
        generator.add_subtitle("Overall Statistics")
        
        total_students = summaries.count()
        total_days = summaries.aggregate(total=Sum('total_days'))['total'] or 0
        total_present = summaries.aggregate(total=Sum('present_days'))['total'] or 0
        total_absent = summaries.aggregate(total=Sum('absent_days'))['total'] or 0
        total_late = summaries.aggregate(total=Sum('late_days'))['total'] or 0
        
        avg_rate = (total_present / total_days * 100) if total_days > 0 else 0
        avg_daily_present = total_present / 30 if total_present > 0 else 0  # Approximate
        
        stats_data = [
            ['Total Students', str(total_students)],
            ['Total School Days', str(summaries.first().total_days if summaries.exists() else 0)],
            ['Total Attendance Records', str(total_days)],
            ['Total Present Days', str(total_present)],
            ['Total Absent Days', str(total_absent)],
            ['Total Late Days', str(total_late)],
            ['Average Attendance Rate', f"{avg_rate:.1f}%"],
            ['Average Daily Present', f"{avg_daily_present:.1f}"],
        ]
        
        generator.add_table(stats_data, col_widths=[3*inch, 3*inch])
        
        # Class-wise Summary
        generator.add_subtitle("Class-wise Performance")
        
        class_data = [['Class', 'Students', 'Avg Rate', 'Total Present', 'Total Absent']]
        
        for level in range(1, 5):
            for stream in ['East', 'West', 'North', 'South']:
                class_summaries = summaries.filter(
                    student__current_class=level,
                    student__stream=stream
                )
                if class_summaries.exists():
                    class_total = class_summaries.count()
                    class_present = class_summaries.aggregate(total=Sum('present_days'))['total'] or 0
                    class_absent = class_summaries.aggregate(total=Sum('absent_days'))['total'] or 0
                    class_days = class_summaries.aggregate(total=Sum('total_days'))['total'] or 0
                    class_rate = (class_present / class_days * 100) if class_days > 0 else 0
                    
                    class_data.append([
                        f"Form {level} {stream}",
                        str(class_total),
                        f"{class_rate:.1f}%",
                        str(class_present),
                        str(class_absent)
                    ])
        
        generator.add_table(class_data, col_widths=[1.5*inch, 1*inch, 1*inch, 1.2*inch, 1.2*inch])
        
        # Individual Student Summary
        generator.add_page_break()
        generator.add_subtitle("Individual Student Attendance")
        
        student_data = [['#', 'Admission', 'Student Name', 'Class', 'Present', 'Absent', 'Late', 'Rate']]
        
        for i, summary in enumerate(summaries.order_by('-attendance_percentage'), 1):
            student_data.append([
                str(i),
                summary.student.admission_number,
                summary.student.get_full_name(),
                summary.student.get_current_class_name(),
                str(summary.present_days),
                str(summary.absent_days),
                str(summary.late_days),
                f"{summary.attendance_percentage:.1f}%"
            ])
        
        generator.add_table(student_data, col_widths=[0.4*inch, 1*inch, 1.5*inch, 0.8*inch, 0.6*inch, 0.6*inch, 0.6*inch, 0.8*inch])
        
        generator.add_signature_block()
        
        return generator.generate()
    
    @staticmethod
    def generate_term_report(term):
        """Generate term attendance report"""
        
        from reports.report_generator import ReportGenerator
        
        generator = ReportGenerator(f"Term Attendance Report - {term}")
        generator.add_header_info()
        
        # Get attendance for the term
        attendance = Attendance.objects.filter(
            date__gte=term.start_date,
            date__lte=term.end_date
        )
        
        if not attendance.exists():
            generator.add_paragraph("No attendance records for this term.")
            return generator.generate()
        
        # Term Statistics
        generator.add_subtitle("Term Statistics")
        
        total_days = attendance.dates('date', 'day').count()
        total_records = attendance.count()
        present = attendance.filter(status='present').count()
        absent = attendance.filter(status='absent').count()
        late = attendance.filter(status='late').count()
        
        # Get unique students
        students_count = attendance.values('student').distinct().count()
        
        stats_data = [
            ['School Days', str(total_days)],
            ['Total Students', str(students_count)],
            ['Total Attendance Records', str(total_records)],
            ['Average Daily Attendance', f"{total_records/total_days:.1f}" if total_days > 0 else '0'],
            ['Total Present', str(present)],
            ['Total Absent', str(absent)],
            ['Total Late', str(late)],
            ['Overall Attendance Rate', f"{(present/total_records*100):.1f}%" if total_records > 0 else '0%'],
        ]
        
        generator.add_table(stats_data, col_widths=[3*inch, 3*inch])
        
        # Monthly Breakdown
        generator.add_subtitle("Monthly Breakdown")
        
        months = attendance.dates('date', 'month')
        monthly_data = [['Month', 'Days', 'Present', 'Absent', 'Late', 'Rate']]
        
        for month_date in months:
            month_attendance = attendance.filter(date__year=month_date.year, date__month=month_date.month)
            month_days = month_attendance.dates('date', 'day').count()
            month_present = month_attendance.filter(status='present').count()
            month_absent = month_attendance.filter(status='absent').count()
            month_late = month_attendance.filter(status='late').count()
            month_total = month_attendance.count()
            month_rate = (month_present / month_total * 100) if month_total > 0 else 0
            
            monthly_data.append([
                month_date.strftime('%B %Y'),
                str(month_days),
                str(month_present),
                str(month_absent),
                str(month_late),
                f"{month_rate:.1f}%"
            ])
        
        generator.add_table(monthly_data, col_widths=[1.5*inch, 0.8*inch, 0.8*inch, 0.8*inch, 0.8*inch, 0.8*inch])
        
        # Class Performance
        generator.add_page_break()
        generator.add_subtitle("Class Performance")
        
        class_data = [['Class', 'Students', 'Present', 'Absent', 'Rate']]
        
        for level in range(1, 5):
            for stream in ['East', 'West', 'North', 'South']:
                class_attendance = attendance.filter(class_level=level, stream=stream)
                if class_attendance.exists():
                    class_students = class_attendance.values('student').distinct().count()
                    class_present = class_attendance.filter(status='present').count()
                    class_absent = class_attendance.filter(status='absent').count()
                    class_total = class_attendance.count()
                    class_rate = (class_present / class_total * 100) if class_total > 0 else 0
                    
                    class_data.append([
                        f"Form {level} {stream}",
                        str(class_students),
                        str(class_present),
                        str(class_absent),
                        f"{class_rate:.1f}%"
                    ])
        
        generator.add_table(class_data, col_widths=[1.5*inch, 1*inch, 1.2*inch, 1.2*inch, 1*inch])
        
        generator.add_signature_block()
        
        return generator.generate()
    
    @staticmethod
    def generate_teacher_attendance_report(start_date, end_date):
        """Generate teacher attendance report"""
        
        from reports.report_generator import ReportGenerator
        
        generator = ReportGenerator(f"Teacher Attendance Report: {start_date} to {end_date}")
        generator.add_header_info()
        
        # Get teacher attendance
        attendance = TeacherAttendance.objects.filter(
            date__gte=start_date,
            date__lte=end_date
        ).select_related('teacher')
        
        if not attendance.exists():
            generator.add_paragraph("No teacher attendance records for this period.")
            return generator.generate()
        
        # Overall Statistics
        generator.add_subtitle("Overall Statistics")
        
        total_records = attendance.count()
        present = attendance.filter(status='present').count()
        absent = attendance.filter(status='absent').count()
        late = attendance.filter(status='late').count()
        leave = attendance.filter(status='leave').count()
        
        stats_data = [
            ['Total Records', str(total_records)],
            ['Present', str(present)],
            ['Absent', str(absent)],
            ['Late', str(late)],
            ['On Leave', str(leave)],
            ['Attendance Rate', f"{(present/total_records*100):.1f}%" if total_records > 0 else '0%'],
        ]
        
        generator.add_table(stats_data, col_widths=[3*inch, 3*inch])
        
        # Teacher-wise Summary
        generator.add_subtitle("Teacher-wise Summary")
        
        teacher_stats = {}
        for record in attendance:
            teacher_id = record.teacher.id
            if teacher_id not in teacher_stats:
                teacher_stats[teacher_id] = {
                    'name': record.teacher.get_full_name(),
                    'total': 0,
                    'present': 0,
                    'absent': 0,
                    'late': 0,
                    'leave': 0
                }
            teacher_stats[teacher_id]['total'] += 1
            teacher_stats[teacher_id][record.status] += 1
        
        teacher_data = [['Teacher', 'Present', 'Absent', 'Late', 'Leave', 'Rate']]
        
        for stats in teacher_stats.values():
            rate = (stats['present'] / stats['total'] * 100) if stats['total'] > 0 else 0
            teacher_data.append([
                stats['name'],
                str(stats['present']),
                str(stats['absent']),
                str(stats['late']),
                str(stats['leave']),
                f"{rate:.1f}%"
            ])
        
        generator.add_table(teacher_data, col_widths=[2*inch, 0.8*inch, 0.8*inch, 0.8*inch, 0.8*inch, 0.8*inch])
        
        generator.add_signature_block()
        
        return generator.generate()
    
    @staticmethod
    def generate_late_comers_report(start_date, end_date):
        """Generate report of students who come late frequently"""
        
        from reports.report_generator import ReportGenerator
        
        generator = ReportGenerator(f"Late Comers Report: {start_date} to {end_date}")
        generator.add_header_info()
        
        # Get late attendance records
        late_records = Attendance.objects.filter(
            date__gte=start_date,
            date__lte=end_date,
            status='late'
        ).select_related('student')
        
        if not late_records.exists():
            generator.add_paragraph("No late records for this period.")
            return generator.generate()
        
        # Group by student
        student_lates = {}
        for record in late_records:
            student_id = record.student.id
            if student_id not in student_lates:
                student_lates[student_id] = {
                    'student': record.student,
                    'count': 0,
                    'total_late_minutes': 0,
                    'records': []
                }
            student_lates[student_id]['count'] += 1
            student_lates[student_id]['total_late_minutes'] += record.late_minutes
            student_lates[student_id]['records'].append(record)
        
        # Summary
        generator.add_subtitle("Summary")
        
        total_students = len(student_lates)
        total_late_instances = late_records.count()
        avg_late_minutes = late_records.aggregate(Avg('late_minutes'))['late_minutes__avg'] or 0
        
        summary_data = [
            ['Total Students with Lates', str(total_students)],
            ['Total Late Instances', str(total_late_instances)],
            ['Average Late Minutes', f"{avg_late_minutes:.1f}"],
        ]
        
        generator.add_table(summary_data, col_widths=[3*inch, 3*inch])
        
        # Detailed List
        generator.add_subtitle("Students by Late Frequency")
        
        # Sort by late count
        sorted_students = sorted(student_lates.values(), key=lambda x: x['count'], reverse=True)
        
        late_data = [['#', 'Admission', 'Student Name', 'Class', 'Late Count', 'Total Minutes', 'Avg Minutes']]
        
        for i, data in enumerate(sorted_students, 1):
            avg_minutes = data['total_late_minutes'] / data['count'] if data['count'] > 0 else 0
            late_data.append([
                str(i),
                data['student'].admission_number,
                data['student'].get_full_name(),
                data['student'].get_current_class_name(),
                str(data['count']),
                str(data['total_late_minutes']),
                f"{avg_minutes:.1f}"
            ])
        
        generator.add_table(late_data, col_widths=[0.4*inch, 1*inch, 1.5*inch, 0.8*inch, 0.8*inch, 0.8*inch, 0.8*inch])
        
        generator.add_signature_block()
        
        return generator.generate()