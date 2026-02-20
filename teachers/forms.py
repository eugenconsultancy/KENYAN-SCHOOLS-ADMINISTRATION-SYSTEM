from django import forms
from django.core.exceptions import ValidationError
from .models import (
    Teacher, TeacherQualification, TeacherSubject, TeacherClass,
    TeacherLeave, TeacherAttendance, TeacherDocument, TeacherPerformance,
    TeacherSalary, TeacherTraining, TeacherAward, TeacherNote
)
from academics.models import Subject, AcademicYear, Term
from accounts.models import User
import datetime

class TeacherForm(forms.ModelForm):
    """Form for creating/editing teachers"""
    
    # User account fields
    username = forms.CharField(max_length=150, required=True)
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=30, required=True)
    last_name = forms.CharField(max_length=30, required=True)
    password = forms.CharField(widget=forms.PasswordInput(), required=False,
                              help_text="Leave blank if you don't want to change password")
    
    class Meta:
        model = Teacher
        fields = '__all__'
        exclude = ['user', 'created_by', 'created_at', 'updated_at']
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
            'date_employed': forms.DateInput(attrs={'type': 'date'}),
            'medical_conditions': forms.Textarea(attrs={'rows': 3}),
            'qualifications': forms.Textarea(attrs={'rows': 4}),
            'physical_address': forms.Textarea(attrs={'rows': 2}),
        }
    
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        
        # Make fields optional/required as needed
        self.fields['alternative_phone'].required = False
        self.fields['physical_address'].required = False
        self.fields['postal_address'].required = False
        self.fields['bank_name'].required = False
        self.fields['bank_branch'].required = False
        self.fields['bank_account'].required = False
        self.fields['bank_code'].required = False
        self.fields['blood_group'].required = False
        self.fields['medical_conditions'].required = False
        self.fields['cv'].required = False
        self.fields['contract'].required = False
        self.fields['passport_photo'].required = False
        self.fields['specialization'].required = False
        
        # If editing, populate user fields
        if self.instance and self.instance.pk:
            self.fields['username'].initial = self.instance.user.username
            self.fields['email'].initial = self.instance.user.email
            self.fields['first_name'].initial = self.instance.user.first_name
            self.fields['last_name'].initial = self.instance.user.last_name
            self.fields['password'].required = False
    
    def clean_employee_number(self):
        employee_number = self.cleaned_data['employee_number']
        if Teacher.objects.filter(employee_number=employee_number).exclude(pk=self.instance.pk).exists():
            raise ValidationError('A teacher with this employee number already exists.')
        return employee_number
    
    def clean_tsc_number(self):
        tsc_number = self.cleaned_data['tsc_number']
        if Teacher.objects.filter(tsc_number=tsc_number).exclude(pk=self.instance.pk).exists():
            raise ValidationError('A teacher with this TSC number already exists.')
        return tsc_number
    
    def clean_id_number(self):
        id_number = self.cleaned_data['id_number']
        if Teacher.objects.filter(id_number=id_number).exclude(pk=self.instance.pk).exists():
            raise ValidationError('A teacher with this ID number already exists.')
        return id_number
    
    def clean_date_of_birth(self):
        dob = self.cleaned_data['date_of_birth']
        age = datetime.date.today().year - dob.year
        if age < 21 or age > 70:
            raise ValidationError('Teacher age must be between 21 and 70 years.')
        return dob
    
    def clean_username(self):
        username = self.cleaned_data['username']
        if User.objects.filter(username=username).exclude(pk=self.instance.user.pk if self.instance.pk else None).exists():
            raise ValidationError('This username is already taken.')
        return username
    
    def clean_email(self):
        email = self.cleaned_data['email']
        if email and User.objects.filter(email=email).exclude(pk=self.instance.user.pk if self.instance.pk else None).exists():
            raise ValidationError('This email is already registered.')
        return email
    
    def save(self, commit=True):
        # Handle user account
        if self.instance.pk:
            # Update existing user
            user = self.instance.user
            user.username = self.cleaned_data['username']
            user.email = self.cleaned_data['email']
            user.first_name = self.cleaned_data['first_name']
            user.last_name = self.cleaned_data['last_name']
            if self.cleaned_data['password']:
                user.set_password(self.cleaned_data['password'])
            user.save()
        else:
            # Create new user
            user = User.objects.create_user(
                username=self.cleaned_data['username'],
                email=self.cleaned_data['email'],
                password=self.cleaned_data['password'] or 'Teacher@123',  # Default password
                first_name=self.cleaned_data['first_name'],
                last_name=self.cleaned_data['last_name'],
                role='teacher'
            )
        
        # Save teacher
        teacher = super().save(commit=False)
        teacher.user = user
        
        if self.request and hasattr(self.request, 'user'):
            teacher.created_by = self.request.user
        
        if commit:
            teacher.save()
        
        return teacher

class TeacherSearchForm(forms.Form):
    """Form for searching teachers"""
    
    query = forms.CharField(max_length=100, required=False, widget=forms.TextInput(attrs={
        'placeholder': 'Search by name, employee number, or TSC number...',
        'class': 'form-control'
    }))
    
    employment_type = forms.ChoiceField(
        choices=[('', 'All Types')] + Teacher.EMPLOYMENT_TYPES,
        required=False
    )
    qualification_level = forms.ChoiceField(
        choices=[('', 'All Qualifications')] + Teacher.QUALIFICATION_LEVELS,
        required=False
    )
    gender = forms.ChoiceField(
        choices=[('', 'All Genders')] + Teacher.GENDER_CHOICES,
        required=False
    )
    is_active = forms.BooleanField(required=False, initial=True, widget=forms.CheckboxInput(attrs={
        'class': 'form-check-input'
    }))

class TeacherQualificationForm(forms.ModelForm):
    """Form for adding teacher qualifications"""
    
    class Meta:
        model = TeacherQualification
        fields = ['qualification', 'institution', 'year_obtained', 'certificate']
        widgets = {
            'year_obtained': forms.NumberInput(attrs={'min': 1950, 'max': datetime.date.today().year}),
        }

class TeacherSubjectForm(forms.ModelForm):
    """Form for assigning subjects to teachers"""
    
    class Meta:
        model = TeacherSubject
        fields = ['subject', 'is_main']

class TeacherClassForm(forms.ModelForm):
    """Form for assigning form classes to teachers"""
    
    class Meta:
        model = TeacherClass
        fields = ['class_level', 'stream', 'academic_year', 'is_current']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['academic_year'].queryset = AcademicYear.objects.all().order_by('-name')

class TeacherLeaveForm(forms.ModelForm):
    """Form for teacher leave requests"""
    
    class Meta:
        model = TeacherLeave
        fields = ['leave_type', 'start_date', 'end_date', 'reason']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
            'reason': forms.Textarea(attrs={'rows': 4}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        
        if start_date and end_date:
            if end_date < start_date:
                raise ValidationError('End date cannot be before start date.')
            
            # Calculate days
            days = (end_date - start_date).days + 1
            if days > 30:
                raise ValidationError('Leave cannot exceed 30 days.')
        
        return cleaned_data

class TeacherAttendanceForm(forms.ModelForm):
    """Form for marking teacher attendance"""
    
    class Meta:
        model = TeacherAttendance
        fields = ['teacher', 'date', 'status', 'check_in_time', 'check_out_time', 'remarks']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'check_in_time': forms.TimeInput(attrs={'type': 'time'}),
            'check_out_time': forms.TimeInput(attrs={'type': 'time'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['date'].initial = datetime.date.today()
        self.fields['remarks'].required = False
        self.fields['check_in_time'].required = False
        self.fields['check_out_time'].required = False

class TeacherDocumentForm(forms.ModelForm):
    """Form for uploading teacher documents"""
    
    class Meta:
        model = TeacherDocument
        fields = ['document_type', 'title', 'file', 'description', 'expiry_date']
        widgets = {
            'expiry_date': forms.DateInput(attrs={'type': 'date'}),
            'description': forms.Textarea(attrs={'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['description'].required = False
        self.fields['expiry_date'].required = False

class TeacherPerformanceForm(forms.ModelForm):
    """Form for teacher performance evaluation"""
    
    class Meta:
        model = TeacherPerformance
        fields = [
            'teacher', 'academic_year', 'term',
            'lesson_preparation', 'lesson_delivery', 'student_assessment',
            'class_management', 'punctuality', 'professional_conduct',
            'co_curricular', 'comments'
        ]
        widgets = {
            'comments': forms.Textarea(attrs={'rows': 4}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['academic_year'].queryset = AcademicYear.objects.all().order_by('-name')
        self.fields['term'].queryset = Term.objects.all().order_by('-academic_year', 'term')
        self.fields['comments'].required = False

class TeacherSalaryForm(forms.ModelForm):
    """Form for teacher salary records"""
    
    class Meta:
        model = TeacherSalary
        fields = [
            'teacher', 'month', 'year', 'basic_salary',
            'house_allowance', 'transport_allowance', 'medical_allowance', 'other_allowances',
            'tax', 'nhif', 'nssf', 'loan_deduction', 'other_deductions',
            'payment_date', 'payment_method', 'payslip'
        ]
        widgets = {
            'payment_date': forms.DateInput(attrs={'type': 'date'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['payment_method'].initial = 'bank_transfer'
        self.fields['payslip'].required = False
        
        # Set default values for allowances and deductions
        for field in ['house_allowance', 'transport_allowance', 'medical_allowance', 
                     'other_allowances', 'tax', 'nhif', 'nssf', 'loan_deduction', 
                     'other_deductions']:
            self.fields[field].initial = 0
    
    def clean(self):
        cleaned_data = super().clean()
        month = cleaned_data.get('month')
        year = cleaned_data.get('year')
        teacher = cleaned_data.get('teacher')
        
        # Check if salary already exists for this teacher/month/year
        if teacher and month and year:
            if TeacherSalary.objects.filter(
                teacher=teacher, month=month, year=year
            ).exclude(pk=self.instance.pk).exists():
                raise ValidationError('Salary record already exists for this teacher for this period.')
        
        return cleaned_data

class TeacherTrainingForm(forms.ModelForm):
    """Form for teacher training records"""
    
    class Meta:
        model = TeacherTraining
        fields = ['title', 'provider', 'start_date', 'end_date', 'duration_days', 'certificate', 'description']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
            'description': forms.Textarea(attrs={'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['description'].required = False
        self.fields['certificate'].required = False
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        
        if start_date and end_date and end_date < start_date:
            raise ValidationError('End date cannot be before start date.')
        
        return cleaned_data

class TeacherAwardForm(forms.ModelForm):
    """Form for teacher awards"""
    
    class Meta:
        model = TeacherAward
        fields = ['award_name', 'awarding_body', 'date_received', 'description', 'certificate']
        widgets = {
            'date_received': forms.DateInput(attrs={'type': 'date'}),
            'description': forms.Textarea(attrs={'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['description'].required = False
        self.fields['certificate'].required = False

class TeacherNoteForm(forms.ModelForm):
    """Form for adding notes to teachers"""
    
    class Meta:
        model = TeacherNote
        fields = ['note_type', 'title', 'content']
        widgets = {
            'content': forms.Textarea(attrs={'rows': 4}),
        }

class TeacherFilterForm(forms.Form):
    """Advanced filter form for teachers"""
    
    employment_type = forms.MultipleChoiceField(
        choices=Teacher.EMPLOYMENT_TYPES,
        widget=forms.CheckboxSelectMultiple,
        required=False
    )
    
    qualification_level = forms.MultipleChoiceField(
        choices=Teacher.QUALIFICATION_LEVELS,
        widget=forms.CheckboxSelectMultiple,
        required=False
    )
    
    gender = forms.ChoiceField(
        choices=[('', 'All')] + list(Teacher.GENDER_CHOICES),
        required=False
    )
    
    years_experience_min = forms.IntegerField(
        required=False,
        widget=forms.NumberInput(attrs={'placeholder': 'Min years'})
    )
    
    years_experience_max = forms.IntegerField(
        required=False,
        widget=forms.NumberInput(attrs={'placeholder': 'Max years'})
    )
    
    is_active = forms.BooleanField(required=False, initial=True)

class TeacherBulkUploadForm(forms.Form):
    """Form for bulk uploading teachers via CSV"""
    
    csv_file = forms.FileField(label='CSV File', help_text='Upload a CSV file with teacher data')
    
    def clean_csv_file(self):
        file = self.cleaned_data['csv_file']
        if not file.name.endswith('.csv'):
            raise ValidationError('Please upload a CSV file.')
        return file