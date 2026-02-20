from django import forms
from django.core.exceptions import ValidationError
from .models import (
    Attendance, TeacherAttendance, AttendanceSession, DailyAttendanceRegister,
    Holiday, AttendanceReport, AttendanceNotification
)
from students.models import Student
from teachers.models import Teacher
from academics.models import Class
import datetime

class AttendanceSessionForm(forms.ModelForm):
    """Form for attendance sessions"""
    
    class Meta:
        model = AttendanceSession
        fields = ['name', 'session_type', 'start_time', 'end_time', 'is_active']
        widgets = {
            'start_time': forms.TimeInput(attrs={'type': 'time'}),
            'end_time': forms.TimeInput(attrs={'type': 'time'}),
        }

class AttendanceForm(forms.ModelForm):
    """Form for marking student attendance"""
    
    class Meta:
        model = Attendance
        fields = ['student', 'date', 'session', 'status', 'check_in_time', 'check_out_time', 'reason']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'check_in_time': forms.TimeInput(attrs={'type': 'time'}),
            'check_out_time': forms.TimeInput(attrs={'type': 'time'}),
            'reason': forms.Textarea(attrs={'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['date'].initial = datetime.date.today()
        self.fields['session'].required = False
        self.fields['check_in_time'].required = False
        self.fields['check_out_time'].required = False
        self.fields['reason'].required = False
        
        # Filter students
        self.fields['student'].queryset = Student.objects.filter(is_active=True)

class BulkAttendanceForm(forms.Form):
    """Form for bulk attendance marking"""
    
    date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    session = forms.ModelChoiceField(queryset=AttendanceSession.objects.filter(is_active=True), required=False)
    class_level = forms.ChoiceField(choices=Student.CLASS_LEVELS)
    stream = forms.ChoiceField(choices=Student.STREAMS)
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['date'].initial = datetime.date.today()

class TeacherAttendanceForm(forms.ModelForm):
    """Form for marking teacher attendance"""
    
    class Meta:
        model = TeacherAttendance
        fields = ['teacher', 'date', 'status', 'check_in_time', 'check_out_time', 'reason']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'check_in_time': forms.TimeInput(attrs={'type': 'time'}),
            'check_out_time': forms.TimeInput(attrs={'type': 'time'}),
            'reason': forms.Textarea(attrs={'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['date'].initial = datetime.date.today()
        self.fields['check_in_time'].required = False
        self.fields['check_out_time'].required = False
        self.fields['reason'].required = False
        self.fields['teacher'].queryset = Teacher.objects.filter(is_active=True)

class DateRangeForm(forms.Form):
    """Form for date range selection"""
    
    start_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    end_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        
        if start_date and end_date and end_date < start_date:
            raise ValidationError('End date cannot be before start date.')
        
        return cleaned_data

class HolidayForm(forms.ModelForm):
    """Form for holidays"""
    
    class Meta:
        model = Holiday
        fields = ['name', 'holiday_type', 'date', 'description', 'is_recurring']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'description': forms.Textarea(attrs={'rows': 3}),
        }

class AttendanceReportForm(forms.ModelForm):
    """Form for generating attendance reports"""
    
    class Meta:
        model = AttendanceReport
        fields = ['title', 'report_type', 'start_date', 'end_date', 'class_level', 'stream']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['class_level'].required = False
        self.fields['stream'].required = False
        
        # Set default date range (current month)
        today = datetime.date.today()
        self.fields['start_date'].initial = today.replace(day=1)
        self.fields['end_date'].initial = today

class AttendanceFilterForm(forms.Form):
    """Form for filtering attendance records"""
    
    start_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    end_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    class_level = forms.ChoiceField(
        choices=[('', 'All Classes')] + list(Student.CLASS_LEVELS),
        required=False
    )
    stream = forms.ChoiceField(
        choices=[('', 'All Streams')] + list(Student.STREAMS),
        required=False
    )
    status = forms.ChoiceField(
        choices=[('', 'All Status')] + list(Attendance.ATTENDANCE_STATUS),
        required=False
    )

class AttendanceNotificationForm(forms.ModelForm):
    """Form for sending attendance notifications"""
    
    class Meta:
        model = AttendanceNotification
        fields = ['student', 'attendance', 'notification_type', 'recipient_phone', 'message']
        widgets = {
            'message': forms.Textarea(attrs={'rows': 4}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['recipient_phone'].required = False
        self.fields['message'].initial = "Your child was marked absent from school today. Please contact the school for more information."