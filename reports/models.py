from django.db import models
from django.conf import settings
from accounts.models import User
import os

class GeneratedReport(models.Model):
    """Model to track generated reports"""
    
    REPORT_TYPES = [
        ('student', 'Student Report'),
        ('class', 'Class Report'),
        ('attendance', 'Attendance Report'),
        ('result', 'Result Report'),
        ('finance', 'Finance Report'),
        ('teacher', 'Teacher Report'),
        ('custom', 'Custom Report'),
    ]
    
    title = models.CharField(max_length=200)
    report_type = models.CharField(max_length=20, choices=REPORT_TYPES)
    
    # File
    file = models.FileField(upload_to='reports/generated/')
    file_size = models.IntegerField(help_text="File size in bytes", null=True, blank=True)
    
    # Metadata
    generated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    generated_at = models.DateTimeField(auto_now_add=True)
    
    # Filters used
    filters = models.JSONField(default=dict, blank=True)
    
    class Meta:
        ordering = ['-generated_at']
    
    def __str__(self):
        return f"{self.title} - {self.generated_at.strftime('%Y-%m-%d %H:%M')}"
    
    def delete(self, *args, **kwargs):
        # Delete the file when model is deleted
        if self.file:
            if os.path.isfile(self.file.path):
                os.remove(self.file.path)
        super().delete(*args, **kwargs)
    
    def get_file_size_display(self):
        """Get human readable file size"""
        if not self.file_size:
            return "Unknown"
        
        size = self.file_size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"

class ReportSchedule(models.Model):
    """Schedule automated report generation"""
    
    FREQUENCY_CHOICES = [
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('termly', 'Termly'),
    ]
    
    name = models.CharField(max_length=100)
    report_type = models.CharField(max_length=20, choices=GeneratedReport.REPORT_TYPES)
    frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES)
    
    # Filters to apply
    filters = models.JSONField(default=dict)
    
    # Recipients
    recipients = models.ManyToManyField(User, related_name='scheduled_reports')
    
    # Schedule
    next_run = models.DateTimeField()
    last_run = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    
    # Metadata
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_schedules')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['next_run']
    
    def __str__(self):
        return f"{self.name} - {self.get_frequency_display()}"