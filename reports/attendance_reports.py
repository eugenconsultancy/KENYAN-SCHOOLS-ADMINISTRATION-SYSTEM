"""
Attendance Reports Module
Handles generation of attendance-related reports
"""

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from django.utils import timezone
from django.db.models import Count, Q, Sum
from .report_generator import ReportGenerator
from attendance.models import Attendance, AttendanceSummary, Holiday
from students.models import Student
import datetime
import calendar

class AttendanceReportGenerator(ReportGenerator):
    """Generator for attendance reports"""
    
    @staticmethod
    def generate_attendance_report(start_date, end_date, class_level=None, stream=None):
        """Generate attendance report for date range"""
        
        title = "Attendance Report"
        if class_level:
            title += f" - Form {class_level}"
            if stream:
                title += f" {stream}"
        
        generator = ReportGenerator(title)
        generator.add_header_info(
            Period=f"{start_date} to {end_date}",
            Class=f"Form {class_level} {stream}" if class_level else "All Classes"
        )
        
        # Get attendance records
        attendance = Attendance.objects.filter(
            date__gte=start_date,
            date__lte=end_date
        )
        
        if class_level:
            attendance = attendance.filter(class_level=class_level)
        if stream:
            attendance = attendance.filter(stream=stream)
        
        # Overall Statistics
        generator.add_subtitle("Overall Statistics")
        
        total_records = attendance.count()
        present = attendance.filter(status='present').count()
        absent = attendance.filter(status='absent').count()
        late = attendance.filter(status='late').count()
        excused = attendance.filter(status__in=['excused', 'sick', 'sports', 'official']).count()
        
        stats_data = [
            ['Metric', 'Count', 'Percentage'],
            ['Total Records', str(total_records), '100%'],
            ['Present', str(present), f"{(present/total_records*100):.1f}%" if total_records > 0 else '0%'],
            ['Absent', str(absent), f"{(absent/total_records*100):.1f}%" if total_records > 0 else '0%'],
            ['Late', str(late), f"{(late/total_records*100):.1f}%" if total_records > 0 else '0%'],
            ['Excused', str(excused), f"{(excused/total_records*100):.1f}%" if total_records > 0 else '0%'],
        ]
        
        generator.add_table(stats_data, col_widths=[2*inch, 1.5*inch, 1.5*inch])
        
        # Daily Breakdown
        generator.add_subtitle("Daily Attendance Breakdown")
        
        dates = attendance.dates('date', 'day').order_by('date')
        daily_data = [['Date', 'Present', 'Absent', 'Late', 'Excused', 'Total', 'Rate']]
        
        for date in dates:
            day_records = attendance.filter(date=date)
            day_present = day_records.filter(status='present').count()
            day_absent = day_records.filter(status='absent').count()
            day_late = day_records.filter(status='late').count()
            day_excused = day_records.filter(status__in=['excused', 'sick', 'sports', 'official']).count()
            day_total = day_records.count()
            day_rate = (day_present / day_total * 100) if day_total > 0 else 0
            
            daily_data.append([
                date.strftime('%Y-%m-%d'),
                str(day_present),
                str(day_absent),
                str(day_late),
                str(day_excused),
                str(day_total),
                f"{day_rate:.1f}%"
            ])
        
        generator.add_table(daily_data, col_widths=[1.2*inch, 0.8*inch, 0.8*inch, 0.8*inch, 0.8*inch, 0.8*inch, 0.8*inch])
        
        # Class-wise Breakdown (if not filtered by class)
        if not class_level:
            generator.add_page_break()
            generator.add_subtitle("Class-wise Attendance Summary")
            
            class_data = [['Class', 'Present', 'Absent', 'Late', 'Total', 'Rate']]
            
            for level in range(1, 5):
                for strm in ['East', 'West', 'North', 'South']:
                    class_records = attendance.filter(class_level=level, stream=strm)
                    if class_records.exists():
                        class_present = class_records.filter(status='present').count()
                        class_absent = class_records.filter(status='absent').count()
                        class_late = class_records.filter(status='late').count()
                        class_total = class_records.count()
                        class_rate = (class_present / class_total * 100) if class_total > 0 else 0
                        
                        class_data.append([
                            f"Form {level} {strm}",
                            str(class_present),
                            str(class_absent),
                            str(class_late),
                            str(class_total),
                            f"{class_rate:.1f}%"
                        ])
            
            generator.add_table(class_data, col_widths=[1.5*inch, 0.8*inch, 0.8*inch, 0.8*inch, 0.8*inch, 0.8*inch])
        
        # Top/Bottom Performers
        generator.add_page_break()
        generator.add_subtitle("Top 10 Students by Attendance")
        
        # Get students with best attendance
        students = Student.objects.filter(is_active=True)
        if class_level:
            students = students.filter(current_class=class_level)
        if stream:
            students = students.filter(stream=stream)
        
        student_stats = []
        for student in students:
            student_records = attendance.filter(student=student)
            if student_records.exists():
                student_present = student_records.filter(status='present').count()
                student_total = student_records.count()
                student_rate = (student_present / student_total * 100)
                student_stats.append({
                    'name': student.get_full_name(),
                    'admission': student.admission_number,
                    'class': f"F{student.current_class}{student.stream}",
                    'rate': student_rate,
                    'present': student_present,
                    'total': student_total
                })
        
        # Sort by attendance rate
        student_stats.sort(key=lambda x: x['rate'], reverse=True)
        
        top_data = [['#', 'Admission No.', 'Name', 'Class', 'Present/Total', 'Rate']]
        for i, stat in enumerate(student_stats[:10], 1):
            top_data.append([
                str(i),
                stat['admission'],
                stat['name'],
                stat['class'],
                f"{stat['present']}/{stat['total']}",
                f"{stat['rate']:.1f}%"
            ])
        
        generator.add_table(top_data, col_widths=[0.4*inch, 1*inch, 1.8*inch, 0.8*inch, 1*inch, 0.8*inch])
        
        generator.add_subtitle("Bottom 10 Students by Attendance")
        
        bottom_data = [['#', 'Admission No.', 'Name', 'Class', 'Present/Total', 'Rate']]
        for i, stat in enumerate(student_stats[-10:], 1):
            bottom_data.append([
                str(i),
                stat['admission'],
                stat['name'],
                stat['class'],
                f"{stat['present']}/{stat['total']}",
                f"{stat['rate']:.1f}%"
            ])
        
        generator.add_table(bottom_data, col_widths=[0.4*inch, 1*inch, 1.8*inch, 0.8*inch, 1*inch, 0.8*inch])
        
        generator.add_signature_block()
        
        return generator.generate()
    
    @staticmethod
    def generate_student_attendance_report(student, start_date=None, end_date=None):
        """Generate individual student attendance report"""
        
        generator = ReportGenerator(f"Attendance Report: {student.get_full_name()}")
        generator.add_header_info(
            Admission=student.admission_number,
            Class=student.get_current_class_name()
        )
        
        # Get attendance records
        attendance = Attendance.objects.filter(student=student).order_by('-date')
        
        if start_date and end_date:
            attendance = attendance.filter(date__gte=start_date, date__lte=end_date)
            period = f"{start_date} to {end_date}"
        else:
            # Default to current term
            from academics.models import Term
            current_term = Term.objects.filter(is_current=True).first()
            if current_term:
                attendance = attendance.filter(
                    date__gte=current_term.start_date,
                    date__lte=current_term.end_date
                )
                period = f"Term {current_term.term}, {current_term.academic_year}"
            else:
                period = "All Time"
        
        generator.add_paragraph(f"Period: {period}")
        
        # Summary Statistics
        generator.add_subtitle("Attendance Summary")
        
        total_days = attendance.count()
        present = attendance.filter(status='present').count()
        absent = attendance.filter(status='absent').count()
        late = attendance.filter(status='late').count()
        excused = attendance.filter(status__in=['excused', 'sick']).count()
        
        if total_days > 0:
            attendance_rate = (present / total_days * 100)
        else:
            attendance_rate = 0
        
        summary_data = [
            ['Metric', 'Count'],
            ['Total School Days', str(total_days)],
            ['Days Present', str(present)],
            ['Days Absent', str(absent)],
            ['Days Late', str(late)],
            ['Excused Days', str(excused)],
            ['Attendance Rate', f"{attendance_rate:.1f}%"],
        ]
        
        generator.add_table(summary_data, col_widths=[2.5*inch, 2.5*inch])
        
        # Monthly Breakdown
        if attendance.exists():
            generator.add_subtitle("Monthly Breakdown")
            
            # Group by month
            monthly_stats = {}
            for record in attendance:
                key = f"{record.date.year}-{record.date.month:02d}"
                if key not in monthly_stats:
                    monthly_stats[key] = {
                        'total': 0,
                        'present': 0,
                        'absent': 0,
                        'late': 0,
                        'excused': 0
                    }
                
                monthly_stats[key]['total'] += 1
                if record.status == 'present':
                    monthly_stats[key]['present'] += 1
                elif record.status == 'absent':
                    monthly_stats[key]['absent'] += 1
                elif record.status == 'late':
                    monthly_stats[key]['late'] += 1
                else:
                    monthly_stats[key]['excused'] += 1
            
            monthly_data = [['Month', 'Present', 'Absent', 'Late', 'Excused', 'Rate']]
            for month_key in sorted(monthly_stats.keys(), reverse=True):
                stats = monthly_stats[month_key]
                rate = (stats['present'] / stats['total'] * 100) if stats['total'] > 0 else 0
                
                year, month = month_key.split('-')
                month_name = calendar.month_name[int(month)]
                
                monthly_data.append([
                    f"{month_name} {year}",
                    str(stats['present']),
                    str(stats['absent']),
                    str(stats['late']),
                    str(stats['excused']),
                    f"{rate:.1f}%"
                ])
            
            generator.add_table(monthly_data, col_widths=[1.5*inch, 0.8*inch, 0.8*inch, 0.8*inch, 0.8*inch, 0.8*inch])
        
        # Detailed Records
        generator.add_page_break()
        generator.add_subtitle("Detailed Attendance Records")
        
        detail_data = [['Date', 'Day', 'Status', 'Session', 'Remarks']]
        for record in attendance[:100]:  # Limit to last 100 records
            detail_data.append([
                record.date.strftime('%Y-%m-%d'),
                record.date.strftime('%A'),
                record.get_status_display(),
                record.session.name if record.session else 'N/A',
                record.reason[:50] + ('...' if len(record.reason) > 50 else '') if record.reason else '-'
            ])
        
        generator.add_table(detail_data, col_widths=[1*inch, 1*inch, 1*inch, 1*inch, 2*inch])
        
        generator.add_signature_block()
        
        return generator.generate()
    
    @staticmethod
    def generate_monthly_summary(year, month, class_level=None):
        """Generate monthly attendance summary"""
        
        month_name = calendar.month_name[int(month)]
        title = f"Attendance Summary - {month_name} {year}"
        if class_level:
            title += f" - Form {class_level}"
        
        generator = ReportGenerator(title)
        generator.add_header_info()
        
        # Get all days in month
        num_days = calendar.monthrange(year, month)[1]
        start_date = datetime.date(year, month, 1)
        end_date = datetime.date(year, month, num_days)
        
        # Get holidays in this month
        holidays = Holiday.objects.filter(date__month=month, date__year=year)
        holiday_dates = [h.date for h in holidays]
        
        # Calculate daily statistics
        daily_stats = []
        total_present = 0
        total_students = 0
        school_days = 0
        
        for day in range(1, num_days + 1):
            date = datetime.date(year, month, day)
            
            # Skip weekends and holidays
            if date.weekday() >= 5 or date in holiday_dates:
                continue
            
            school_days += 1
            
            # Get attendance for this day
            attendance = Attendance.objects.filter(date=date)
            if class_level:
                attendance = attendance.filter(class_level=class_level)
            
            day_total = attendance.count()
            day_present = attendance.filter(status='present').count()
            day_rate = (day_present / day_total * 100) if day_total > 0 else 0
            
            total_present += day_present
            total_students += day_total
            
            daily_stats.append({
                'date': date,
                'total': day_total,
                'present': day_present,
                'rate': day_rate
            })
        
        # Overall Statistics
        generator.add_subtitle("Monthly Statistics")
        
        avg_rate = (total_present / total_students * 100) if total_students > 0 else 0
        avg_daily_present = total_present / school_days if school_days > 0 else 0
        
        stats_data = [
            ['Metric', 'Value'],
            ['School Days', str(school_days)],
            ['Total Attendance Records', str(total_students)],
            ['Total Present', str(total_present)],
            ['Average Daily Present', f"{avg_daily_present:.1f}"],
            ['Average Attendance Rate', f"{avg_rate:.1f}%"],
        ]
        
        generator.add_table(stats_data, col_widths=[3*inch, 3*inch])
        
        # Daily Breakdown
        generator.add_subtitle("Daily Attendance")
        
        daily_data = [['Date', 'Day', 'Total Students', 'Present', 'Rate']]
        for stat in daily_stats:
            daily_data.append([
                stat['date'].strftime('%Y-%m-%d'),
                stat['date'].strftime('%A'),
                str(stat['total']),
                str(stat['present']),
                f"{stat['rate']:.1f}%"
            ])
        
        generator.add_table(daily_data, col_widths=[1*inch, 1.2*inch, 1.2*inch, 1*inch, 1*inch])
        
        # Class-wise Breakdown (if not filtered by class)
        if not class_level:
            generator.add_page_break()
            generator.add_subtitle("Class-wise Performance")
            
            class_data = [['Class', 'Total Days', 'Present', 'Rate']]
            
            for level in range(1, 5):
                for stream in ['East', 'West', 'North', 'South']:
                    class_attendance = Attendance.objects.filter(
                        date__gte=start_date,
                        date__lte=end_date,
                        class_level=level,
                        stream=stream
                    )
                    
                    if class_attendance.exists():
                        class_total = class_attendance.count()
                        class_present = class_attendance.filter(status='present').count()
                        class_rate = (class_present / class_total * 100) if class_total > 0 else 0
                        
                        class_data.append([
                            f"Form {level} {stream}",
                            str(class_total),
                            str(class_present),
                            f"{class_rate:.1f}%"
                        ])
            
            generator.add_table(class_data, col_widths=[1.5*inch, 1.5*inch, 1.5*inch, 1.5*inch])
        
        generator.add_signature_block()
        
        return generator.generate()