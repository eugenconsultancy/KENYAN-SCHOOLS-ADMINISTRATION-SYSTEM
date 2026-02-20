from django import forms
from django.core.exceptions import ValidationError
from .models import (
    AcademicYear, Term, Subject, SubjectCategory, Class,
    SubjectAllocation, Exam, ExamSchedule, Result,
    Timetable, LessonPlan, Homework, HomeworkSubmission
)
from students.models import Student
from teachers.models import Teacher
import datetime

class AcademicYearForm(forms.ModelForm):
    """Form for academic years"""
    
    class Meta:
        model = AcademicYear
        fields = ['name', 'start_date', 'end_date', 'is_current']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        
        if start_date and end_date and end_date <= start_date:
            raise ValidationError('End date must be after start date.')
        
        return cleaned_data

class TermForm(forms.ModelForm):
    """Form for terms"""
    
    class Meta:
        model = Term
        fields = ['academic_year', 'term', 'start_date', 'end_date', 'is_current', 'closing_date', 'reporting_date']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
            'closing_date': forms.DateInput(attrs={'type': 'date'}),
            'reporting_date': forms.DateInput(attrs={'type': 'date'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['closing_date'].required = False
        self.fields['reporting_date'].required = False
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        academic_year = cleaned_data.get('academic_year')
        
        if start_date and end_date and end_date <= start_date:
            raise ValidationError('End date must be after start date.')
        
        # Check if dates are within academic year
        if academic_year and start_date and (start_date < academic_year.start_date or start_date > academic_year.end_date):
            raise ValidationError('Term start date must be within the academic year.')
        
        return cleaned_data

class SubjectCategoryForm(forms.ModelForm):
    """Form for subject categories"""
    
    class Meta:
        model = SubjectCategory
        fields = ['name', 'code', 'description']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }

class SubjectForm(forms.ModelForm):
    """Form for subjects"""
    
    class Meta:
        model = Subject
        fields = ['name', 'code', 'category', 'subject_type', 'classes', 
                 'pass_mark', 'max_mark', 'description', 'is_active']
        widgets = {
            'classes': forms.CheckboxSelectMultiple(),
            'description': forms.Textarea(attrs={'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Convert JSON field to multiple choice
        if self.instance.pk and self.instance.classes:
            self.initial['classes'] = self.instance.classes

class ClassForm(forms.ModelForm):
    """Form for classes"""
    
    class Meta:
        model = Class
        fields = ['class_level', 'stream', 'academic_year', 'class_teacher', 'capacity']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['class_teacher'].required = False
        self.fields['class_teacher'].queryset = Teacher.objects.filter(is_active=True)

class SubjectAllocationForm(forms.ModelForm):
    """Form for subject allocation"""
    
    class Meta:
        model = SubjectAllocation
        fields = ['subject', 'teacher', 'lessons_per_week']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['teacher'].required = False
        self.fields['teacher'].queryset = Teacher.objects.filter(is_active=True)

class ExamForm(forms.ModelForm):
    """Form for exams"""
    
    class Meta:
        model = Exam
        fields = ['term', 'name', 'exam_type', 'start_date', 'end_date', 'subjects', 'description']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
            'description': forms.Textarea(attrs={'rows': 3}),
            'subjects': forms.CheckboxSelectMultiple(),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['description'].required = False

class ExamScheduleForm(forms.ModelForm):
    """Form for exam schedule"""
    
    class Meta:
        model = ExamSchedule
        fields = ['subject', 'class_assigned', 'date', 'start_time', 'end_time', 'venue']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'start_time': forms.TimeInput(attrs={'type': 'time'}),
            'end_time': forms.TimeInput(attrs={'type': 'time'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['venue'].required = False
    
    def clean(self):
        cleaned_data = super().clean()
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')
        
        if start_time and end_time and end_time <= start_time:
            raise ValidationError('End time must be after start time.')
        
        return cleaned_data

class ResultForm(forms.ModelForm):
    """Form for individual result entry"""
    
    class Meta:
        model = Result
        fields = ['student', 'exam', 'subject', 'marks', 'remarks']
        widgets = {
            'remarks': forms.Textarea(attrs={'rows': 2}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['remarks'].required = False

class ResultBulkUploadForm(forms.Form):
    """Form for bulk uploading results via CSV"""
    
    csv_file = forms.FileField(label='CSV File', help_text='Upload a CSV file with columns: admission_number, subject_code, marks')
    
    def clean_csv_file(self):
        file = self.cleaned_data['csv_file']
        if not file.name.endswith('.csv'):
            raise ValidationError('Please upload a CSV file.')
        return file

class TimetableForm(forms.ModelForm):
    """Form for timetable entries"""
    
    class Meta:
        model = Timetable
        fields = ['class_assigned', 'term', 'day', 'start_time', 'end_time', 'subject', 'teacher']
        widgets = {
            'start_time': forms.TimeInput(attrs={'type': 'time'}),
            'end_time': forms.TimeInput(attrs={'type': 'time'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['teacher'].required = False
    
    def clean(self):
        cleaned_data = super().clean()
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')
        
        if start_time and end_time and end_time <= start_time:
            raise ValidationError('End time must be after start time.')
        
        return cleaned_data

class LessonPlanForm(forms.ModelForm):
    """Form for lesson plans"""
    
    class Meta:
        model = LessonPlan
        fields = ['subject', 'class_assigned', 'term', 'topic', 'subtopics',
                 'objectives', 'week', 'lesson_number', 'materials', 
                 'activities', 'assessment', 'remarks']
        widgets = {
            'objectives': forms.Textarea(attrs={'rows': 3}),
            'materials': forms.Textarea(attrs={'rows': 2}),
            'activities': forms.Textarea(attrs={'rows': 3}),
            'assessment': forms.Textarea(attrs={'rows': 2}),
            'remarks': forms.Textarea(attrs={'rows': 2}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['materials'].required = False
        self.fields['activities'].required = False
        self.fields['assessment'].required = False
        self.fields['remarks'].required = False

class HomeworkForm(forms.ModelForm):
    """Form for homework assignments"""
    
    class Meta:
        model = Homework
        fields = ['subject', 'class_assigned', 'title', 'description', 'due_date', 'attachments']
        widgets = {
            'due_date': forms.DateInput(attrs={'type': 'date'}),
            'description': forms.Textarea(attrs={'rows': 4}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['attachments'].required = False
    
    def clean_due_date(self):
        due_date = self.cleaned_data['due_date']
        if due_date < datetime.date.today():
            raise ValidationError('Due date cannot be in the past.')
        return due_date

class HomeworkSubmissionForm(forms.ModelForm):
    """Form for homework submissions"""
    
    class Meta:
        model = HomeworkSubmission
        fields = ['content', 'attachment']
        widgets = {
            'content': forms.Textarea(attrs={'rows': 4}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['content'].required = False
        self.fields['attachment'].required = False