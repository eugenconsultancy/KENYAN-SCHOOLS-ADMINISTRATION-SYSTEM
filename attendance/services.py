"""
Services module for Attendance app
Handles business logic for attendance operations
"""

from django.db.models import Count, Sum, Q, Avg
from django.utils import timezone
from .models import (
    Attendance, TeacherAttendance, DailyAttendanceRegister,
    Holiday, AttendanceSummary, AttendanceReport, AttendanceNotification
)
from students.models import Student
from teachers.models import Teacher
from academics.models import Class, Term
import datetime
import calendar
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
import os
from django.conf import settings

class AttendanceService:
    """Service for attendance operations"""
    
    @staticmethod
    def get_daily_summary(date):
        """Get daily attendance summary"""
        
        total_students = Student.objects.filter(is_active=True).count()
        present = Attendance.objects.filter(date=date, status='present').count()
        absent = Attendance.objects.filter(date=date, status='absent').count()
        late = Attendance.objects.filter(date=date, status='late').count()
        excused = Attendance.objects.filter(
            date=date, 
            status__in=['excused', 'sick', 'sports', 'official']
        ).count()
        not_marked = total_students - (present + absent + late + excused)
        
        # By class
        by_class = []
        for class_level in range(1, 5):
            for stream in ['East', 'West', 'North', 'South']:
                class_students = Student.objects.filter(
                    current_class=class_level,
                    stream=stream,
                    is_active=True
                ).count()
                
                if class_students > 0:
                    class_present = Attendance.objects.filter(
                        date=date,
                        class_level=class_level,
                        stream=stream,
                        status='present'
                    ).count()
                    
                    by_class.append({
                        'class': f"Form {class_level} {stream}",
                        'total': class_students,
                        'present': class_present,
                        'percentage': (class_present / class_students * 100) if class_students > 0 else 0
                    })
        
        return {
            'date': date,
            'total_students': total_students,
            'present': present,
            'absent': absent,
            'late': late,
            'excused': excused,
            'not_marked': not_marked,
            'attendance_rate': (present / total_students * 100) if total_students > 0 else 0,
            'by_class': by_class
        }
    
    @staticmethod
    def get_class_attendance_summary(class_level, stream, date):
        """Get attendance summary for a specific class"""
        
        students = Student.objects.filter(
            current_class=class_level,
            stream=stream,
            is_active=True
        )
        
        total = students.count()
        present = Attendance.objects.filter(
            date=date,
            class_level=class_level,
            stream=stream,
            status='present'
        ).count()
        absent = Attendance.objects.filter(
            date=date,
            class_level=class_level,
            stream=stream,
            status='absent'
        ).count()
        late = Attendance.objects.filter(
            date=date,
            class_level=class_level,
            stream=stream,
            status='late'
        ).count()
        
        return {
            'total': total,
            'present': present,
            'absent': absent,
            'late': late,
            'attendance_rate': (present / total * 100) if total > 0 else 0,
            'not_marked': total - (present + absent + late)
        }
    
    @staticmethod
    def get_monthly_summary(month, year):
        """Get monthly attendance summary"""
        
        # Get all days in month
        num_days = calendar.monthrange(year, month)[1]
        
        daily_data = []
        for day in range(1, num_days + 1):
            date = datetime.date(year, month, day)
            
            # Check if it's a holiday
            is_holiday = Holiday.objects.filter(date=date).exists()
            
            if not is_holiday and date.weekday() < 5:  # Weekday
                summary = AttendanceService.get_daily_summary(date)
                daily_data.append({
                    'date': date,
                    'rate': summary['attendance_rate'],
                    'present': summary['present'],
                    'total': summary['total_students']
                })
        
        # Calculate averages
        if daily_data:
            avg_rate = sum(d['rate'] for d in daily_data) / len(daily_data)
            total_present = sum(d['present'] for d in daily_data)
            total_days = len(daily_data)
            avg_daily_present = total_present / total_days if total_days > 0 else 0
        else:
            avg_rate = 0
            avg_daily_present = 0
        
        return {
            'month': month,
            'year': year,
            'total_days': len(daily_data),
            'avg_rate': avg_rate,
            'avg_daily_present': avg_daily_present,
            'daily_data': daily_data
        }
    
    @staticmethod
    def get_term_summary(term):
        """Get attendance summary for a term"""
        
        attendance = Attendance.objects.filter(
            date__gte=term.start_date,
            date__lte=term.end_date
        )
        
        total_records = attendance.count()
        present = attendance.filter(status='present').count()
        
        # Get unique students
        students = attendance.values('student').distinct().count()
        
        return {
            'term': term,
            'total_days': attendance.dates('date', 'day').count(),
            'total_records': total_records,
            'present': present,
            'attendance_rate': (present / total_records * 100) if total_records > 0 else 0,
            'students_tracked': students
        }
    
    @staticmethod
    def update_monthly_summaries(year, month):
        """Update monthly summaries for all students"""
        
        students = Student.objects.filter(is_active=True)
        
        for student in students:
            attendance = Attendance.objects.filter(
                student=student,
                date__year=year,
                date__month=month
            )
            
            if attendance.exists():
                summary, created = AttendanceSummary.objects.update_or_create(
                    student=student,
                    month=month,
                    year=year,
                    defaults={
                        'total_days': attendance.count(),
                        'present_days': attendance.filter(status='present').count(),
                        'absent_days': attendance.filter(status='absent').count(),
                        'late_days': attendance.filter(status='late').count(),
                        'excused_days': attendance.filter(status='excused').count(),
                        'sick_days': attendance.filter(status='sick').count(),
                    }
                )
    
    @staticmethod
    def check_low_attendance(threshold=80):
        """Check for students with low attendance"""
        
        current_term = Term.objects.filter(is_current=True).first()
        if not current_term:
            return []
        
        low_attendance = []
        students = Student.objects.filter(is_active=True)
        
        for student in students:
            attendance = Attendance.objects.filter(
                student=student,
                date__gte=current_term.start_date,
                date__lte=current_term.end_date
            )
            
            if attendance.exists():
                present = attendance.filter(status='present').count()
                percentage = (present / attendance.count() * 100)
                
                if percentage < threshold:
                    low_attendance.append({
                        'student': student,
                        'percentage': percentage,
                        'total_days': attendance.count(),
                        'present_days': present
                    })
        
        return sorted(low_attendance, key=lambda x: x['percentage'])

class ReportService:
    """Service for generating attendance reports"""
    
    @staticmethod
    def generate_attendance_report(report_type, start_date, end_date, class_level=None, stream=None):
        """Generate PDF attendance report"""
        
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.pdfgen import canvas
        from reportlab.lib.utils import ImageReader
        
        # Create filename
        timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
        filename = f"attendance_report_{timestamp}.pdf"
        filepath = os.path.join(settings.MEDIA_ROOT, 'attendance/reports/', filename)
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        # Create PDF
        doc = SimpleDocTemplate(filepath, pagesize=landscape(A4))
        elements = []
        styles = getSampleStyleSheet()
        
        # Title
        title = f"Attendance Report: {report_type.title()}"
        elements.append(Paragraph(title, styles['Title']))
        elements.append(Spacer(1, 0.25*inch))
        
        # Date range
        date_range = f"Period: {start_date} to {end_date}"
        elements.append(Paragraph(date_range, styles['Normal']))
        elements.append(Spacer(1, 0.25*inch))
        
        # Filters
        if class_level:
            filter_text = f"Class: Form {class_level}"
            if stream:
                filter_text += f" {stream}"
            elements.append(Paragraph(filter_text, styles['Normal']))
            elements.append(Spacer(1, 0.25*inch))
        
        # Get data
        attendance = Attendance.objects.filter(
            date__gte=start_date,
            date__lte=end_date
        )
        
        if class_level:
            attendance = attendance.filter(class_level=class_level)
        if stream:
            attendance = attendance.filter(stream=stream)
        
        # Summary statistics
        total_records = attendance.count()
        present = attendance.filter(status='present').count()
        absent = attendance.filter(status='absent').count()
        late = attendance.filter(status='late').count()
        excused = attendance.filter(status__in=['excused', 'sick']).count()
        
        # Create summary table
        summary_data = [
            ['Metric', 'Count', 'Percentage'],
            ['Total Records', total_records, '100%'],
            ['Present', present, f"{(present/total_records*100):.1f}%" if total_records > 0 else '0%'],
            ['Absent', absent, f"{(absent/total_records*100):.1f}%" if total_records > 0 else '0%'],
            ['Late', late, f"{(late/total_records*100):.1f}%" if total_records > 0 else '0%'],
            ['Excused', excused, f"{(excused/total_records*100):.1f}%" if total_records > 0 else '0%'],
        ]
        
        summary_table = Table(summary_data, colWidths=[2*inch, 1*inch, 1*inch])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        elements.append(summary_table)
        elements.append(Spacer(1, 0.5*inch))
        
        # Daily breakdown
        elements.append(Paragraph('Daily Breakdown', styles['Heading2']))
        elements.append(Spacer(1, 0.25*inch))
        
        dates = attendance.dates('date', 'day').order_by('date')
        daily_data = [['Date', 'Present', 'Absent', 'Late', 'Excused', 'Total']]
        
        for date in dates:
            day_records = attendance.filter(date=date)
            daily_data.append([
                date.strftime('%Y-%m-%d'),
                day_records.filter(status='present').count(),
                day_records.filter(status='absent').count(),
                day_records.filter(status='late').count(),
                day_records.filter(status__in=['excused', 'sick']).count(),
                day_records.count()
            ])
        
        daily_table = Table(daily_data)
        daily_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        elements.append(daily_table)
        
        # Build PDF
        doc.build(elements)
        
        # Return relative path
        return f"attendance/reports/{filename}"
    
    @staticmethod
    def generate_student_report(student, start_date, end_date):
        """Generate individual student attendance report"""
        
        attendance = Attendance.objects.filter(
            student=student,
            date__gte=start_date,
            date__lte=end_date
        ).order_by('date')
        
        # Calculate statistics
        total = attendance.count()
        present = attendance.filter(status='present').count()
        absent = attendance.filter(status='absent').count()
        late = attendance.filter(status='late').count()
        excused = attendance.filter(status__in=['excused', 'sick']).count()
        
        return {
            'student': student,
            'start_date': start_date,
            'end_date': end_date,
            'total_days': total,
            'present': present,
            'absent': absent,
            'late': late,
            'excused': excused,
            'attendance_rate': (present / total * 100) if total > 0 else 0,
            'details': attendance
        }

class NotificationService:
    """Service for sending attendance notifications"""
    
    @staticmethod
    def send_attendance_sms(attendance):
        """Send SMS notification for absence"""
        
        student = attendance.student
        parent_phone = student.parent_phone
        
        if not parent_phone:
            return False
        
        # Format message
        message = f"Dear Parent, your child {student.get_full_name()} was marked {attendance.get_status_display()} on {attendance.date}. Reason: {attendance.reason or 'Not specified'}. Please contact the school for more information."
        
        # Create notification record
        notification = AttendanceNotification.objects.create(
            student=student,
            attendance=attendance,
            notification_type='sms',
            recipient_phone=parent_phone,
            message=message,
            status='pending'
        )
        
        # TODO: Integrate with SMS gateway (e.g., Africa's Talking, Twilio)
        # For now, just mark as sent
        notification.status = 'sent'
        notification.sent_at = timezone.now()
        notification.save()
        
        return True
    
    @staticmethod
    def send_bulk_absence_notifications(date=None):
        """Send notifications for all absent students on a given date"""
        
        if not date:
            date = timezone.now().date()
        
        absent_students = Attendance.objects.filter(
            date=date,
            status='absent'
        ).select_related('student')
        
        sent_count = 0
        for attendance in absent_students:
            if NotificationService.send_attendance_sms(attendance):
                sent_count += 1
        
        return sent_count