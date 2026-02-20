from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.urls import reverse
from students.models import Student
from teachers.models import Teacher
from academics.models import Class, Term, AcademicYear
from accounts.models import User
import datetime

class AttendanceSession(models.Model):
    """Attendance session (e.g., Morning, Afternoon)"""
    
    SESSION_TYPES = [
        ('morning', 'Morning Session'),
        ('afternoon', 'Afternoon Session'),
        ('evening', 'Evening Session'),
        ('full_day', 'Full Day'),
    ]
    
    name = models.CharField(max_length=50)
    session_type = models.CharField(max_length=20, choices=SESSION_TYPES, default='morning')
    start_time = models.TimeField()
    end_time = models.TimeField()
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['start_time']
    
    def __str__(self):
        return f"{self.name} ({self.start_time} - {self.end_time})"

class Attendance(models.Model):
    """Student attendance records"""
    
    ATTENDANCE_STATUS = [
        ('present', 'Present'),
        ('absent', 'Absent'),
        ('late', 'Late'),
        ('excused', 'Excused'),
        ('sick', 'Sick'),
        ('sports', 'Sports Event'),
        ('official', 'Official Duty'),
        ('holiday', 'Holiday'),
    ]
    
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='attendance_records')
    date = models.DateField()
    session = models.ForeignKey(AttendanceSession, on_delete=models.PROTECT, null=True, blank=True)
    status = models.CharField(max_length=20, choices=ATTENDANCE_STATUS, default='present')
    
    # Time tracking
    check_in_time = models.TimeField(null=True, blank=True)
    check_out_time = models.TimeField(null=True, blank=True)
    late_minutes = models.IntegerField(default=0)
    
    # Class information
    class_level = models.IntegerField(choices=[(1, 'Form 1'), (2, 'Form 2'), (3, 'Form 3'), (4, 'Form 4')])
    stream = models.CharField(max_length=10, choices=[('East', 'East'), ('West', 'West'), ('North', 'North'), ('South', 'South')])
    
    # Reason for absence (if applicable)
    reason = models.TextField(blank=True)
    
    # Metadata
    marked_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='attendance_marked')
    marked_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-date', 'student__user__first_name']
        unique_together = ['student', 'date', 'session']
        indexes = [
            models.Index(fields=['date', 'class_level', 'stream']),
            models.Index(fields=['student', 'date']),
        ]
    
    def __str__(self):
        return f"{self.student.get_full_name()} - {self.date} - {self.get_status_display()}"
    
    def save(self, *args, **kwargs):
        # Auto-populate class and stream from student
        if self.student:
            self.class_level = self.student.current_class
            self.stream = self.student.stream
            
            # Calculate late minutes if checked in late
            if self.check_in_time and self.status == 'late':
                # Assuming school starts at 8:00 AM
                school_start = datetime.time(8, 0)
                check_in = self.check_in_time
                late = (check_in.hour * 60 + check_in.minute) - (school_start.hour * 60 + school_start.minute)
                self.late_minutes = max(0, late)
        
        super().save(*args, **kwargs)

class TeacherAttendance(models.Model):
    """Teacher attendance records"""
    
    ATTENDANCE_STATUS = [
        ('present', 'Present'),
        ('absent', 'Absent'),
        ('late', 'Late'),
        ('leave', 'On Leave'),
        ('official', 'Official Duty'),
        ('sick', 'Sick Leave'),
    ]
    
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE, related_name='attendance_teacher_records')
    date = models.DateField()
    status = models.CharField(max_length=20, choices=ATTENDANCE_STATUS, default='present')
    
    # Time tracking
    check_in_time = models.TimeField(null=True, blank=True)
    check_out_time = models.TimeField(null=True, blank=True)
    late_minutes = models.IntegerField(default=0)
    
    # Reason
    reason = models.TextField(blank=True)
    
    # Metadata
    marked_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='marked_teacher_attendance')
    marked_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-date']
        unique_together = ['teacher', 'date']
    
    def __str__(self):
        return f"{self.teacher.get_full_name()} - {self.date} - {self.get_status_display()}"
    
    def save(self, *args, **kwargs):
        # Calculate late minutes if checked in late
        if self.check_in_time and self.status == 'late':
            school_start = datetime.time(8, 0)
            check_in = self.check_in_time
            late = (check_in.hour * 60 + check_in.minute) - (school_start.hour * 60 + school_start.minute)
            self.late_minutes = max(0, late)
        
        super().save(*args, **kwargs)

class AttendanceSummary(models.Model):
    """Monthly attendance summary for students"""
    
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='attendance_summaries')
    month = models.IntegerField(choices=[(i, i) for i in range(1, 13)])
    year = models.IntegerField()
    
    # Statistics
    total_days = models.IntegerField(default=0)
    present_days = models.IntegerField(default=0)
    absent_days = models.IntegerField(default=0)
    late_days = models.IntegerField(default=0)
    excused_days = models.IntegerField(default=0)
    sick_days = models.IntegerField(default=0)
    
    attendance_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    
    class Meta:
        ordering = ['-year', '-month']
        unique_together = ['student', 'month', 'year']
    
    def __str__(self):
        return f"{self.student.get_full_name()} - {self.month}/{self.year}"
    
    def calculate_percentage(self):
        if self.total_days > 0:
            return (self.present_days / self.total_days) * 100
        return 0
    
    def save(self, *args, **kwargs):
        self.attendance_percentage = self.calculate_percentage()
        super().save(*args, **kwargs)

class DailyAttendanceRegister(models.Model):
    """Daily attendance register for a class"""
    
    class_assigned = models.ForeignKey(Class, on_delete=models.CASCADE, related_name='attendance_registers')
    date = models.DateField()
    session = models.ForeignKey(AttendanceSession, on_delete=models.PROTECT)
    
    # Statistics
    total_students = models.IntegerField(default=0)
    present_count = models.IntegerField(default=0)
    absent_count = models.IntegerField(default=0)
    late_count = models.IntegerField(default=0)
    excused_count = models.IntegerField(default=0)
    
    # Status
    is_complete = models.BooleanField(default=False)
    closed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='closed_registers')
    closed_at = models.DateTimeField(null=True, blank=True)
    
    # Metadata
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_registers')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-date']
        unique_together = ['class_assigned', 'date', 'session']
    
    def __str__(self):
        return f"{self.class_assigned} - {self.date} - {self.session}"
    
    def update_statistics(self):
        """Update statistics from attendance records"""
        attendance = Attendance.objects.filter(
            class_level=self.class_assigned.class_level,
            stream=self.class_assigned.stream,
            date=self.date,
            session=self.session
        )
        
        self.total_students = attendance.count()
        self.present_count = attendance.filter(status='present').count()
        self.absent_count = attendance.filter(status='absent').count()
        self.late_count = attendance.filter(status='late').count()
        self.excused_count = attendance.filter(
            status__in=['excused', 'sick', 'sports', 'official']
        ).count()
        
        self.save()

class Holiday(models.Model):
    """School holidays and events"""
    
    HOLIDAY_TYPES = [
        ('public', 'Public Holiday'),
        ('school', 'School Holiday'),
        ('sports', 'Sports Day'),
        ('event', 'Special Event'),
        ('closed', 'School Closed'),
    ]
    
    name = models.CharField(max_length=200)
    holiday_type = models.CharField(max_length=20, choices=HOLIDAY_TYPES)
    date = models.DateField()
    description = models.TextField(blank=True)
    is_recurring = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['date']
    
    def __str__(self):
        return f"{self.name} - {self.date}"

class AttendanceReport(models.Model):
    """Generated attendance reports"""
    
    REPORT_TYPES = [
        ('daily', 'Daily Report'),
        ('weekly', 'Weekly Report'),
        ('monthly', 'Monthly Report'),
        ('term', 'Term Report'),
        ('custom', 'Custom Range'),
    ]
    
    title = models.CharField(max_length=200)
    report_type = models.CharField(max_length=20, choices=REPORT_TYPES)
    
    # Date range
    start_date = models.DateField()
    end_date = models.DateField()
    
    # Filters
    class_level = models.IntegerField(choices=[(1, 'Form 1'), (2, 'Form 2'), (3, 'Form 3'), (4, 'Form 4')], null=True, blank=True)
    stream = models.CharField(max_length=10, choices=[('East', 'East'), ('West', 'West'), ('North', 'North'), ('South', 'South')], null=True, blank=True)
    
    # File
    report_file = models.FileField(upload_to='attendance/reports/', null=True, blank=True)
    
    # Metadata
    generated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    generated_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-generated_at']
    
    def __str__(self):
        return f"{self.title} - {self.generated_at.date()}"

class AttendanceNotification(models.Model):
    """Attendance notifications for parents"""
    
    NOTIFICATION_TYPES = [
        ('sms', 'SMS'),
        ('email', 'Email'),
        ('push', 'Push Notification'),
    ]
    
    NOTIFICATION_STATUS = [
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('failed', 'Failed'),
    ]
    
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='attendance_notifications')
    attendance = models.ForeignKey(Attendance, on_delete=models.CASCADE, related_name='notifications')
    
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES, default='sms')
    recipient_phone = models.CharField(max_length=15, blank=True)
    recipient_email = models.EmailField(blank=True)
    message = models.TextField()
    status = models.CharField(max_length=20, choices=NOTIFICATION_STATUS, default='pending')
    sent_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.student.get_full_name()} - {self.attendance.date} - {self.status}"