from django import forms
from django.core.exceptions import ValidationError
from .models import Student, Parent, StudentDocument, Club, Sport, StudentNote
from academics.models import Subject
from accounts.models import User
import datetime

class StudentForm(forms.ModelForm):
    """Form for creating/editing students"""
    
    # User account fields
    username = forms.CharField(max_length=150, required=True)
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=30, required=True)
    last_name = forms.CharField(max_length=30, required=True)
    password = forms.CharField(widget=forms.PasswordInput(), required=False, 
                              help_text="Leave blank if you don't want to change password")
    
    class Meta:
        model = Student
        fields = '__all__'
        exclude = ['user', 'created_by', 'created_at', 'updated_at']
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
            'medical_conditions': forms.Textarea(attrs={'rows': 3}),
            'notes': forms.Textarea(attrs={'rows': 3}),
            'physical_address': forms.Textarea(attrs={'rows': 2}),
        }
    
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        
        # Make fields optional/required as needed
        self.fields['alternative_phone'].required = False
        self.fields['email'].required = False
        self.fields['physical_address'].required = False
        self.fields['postal_address'].required = False
        self.fields['parent_occupation'].required = False
        self.fields['parent_email'].required = False
        self.fields['medical_conditions'].required = False
        self.fields['previous_school'].required = False
        self.fields['notes'].required = False
        
        # If editing, populate user fields
        if self.instance and self.instance.pk:
            self.fields['username'].initial = self.instance.user.username
            self.fields['email'].initial = self.instance.user.email
            self.fields['first_name'].initial = self.instance.user.first_name
            self.fields['last_name'].initial = self.instance.user.last_name
            self.fields['password'].required = False
    
    def clean_admission_number(self):
        admission_number = self.cleaned_data['admission_number']
        # Check if admission number already exists (excluding current instance)
        if Student.objects.filter(admission_number=admission_number).exclude(pk=self.instance.pk).exists():
            raise ValidationError('A student with this admission number already exists.')
        return admission_number
    
    def clean_kcpe_index(self):
        kcpe_index = self.cleaned_data['kcpe_index']
        if Student.objects.filter(kcpe_index=kcpe_index).exclude(pk=self.instance.pk).exists():
            raise ValidationError('A student with this KCPE index already exists.')
        return kcpe_index
    
    def clean_date_of_birth(self):
        dob = self.cleaned_data['date_of_birth']
        age = datetime.date.today().year - dob.year
        if age < 10 or age > 25:
            raise ValidationError('Student age must be between 10 and 25 years.')
        return dob
    
    def clean_username(self):
        username = self.cleaned_data['username']
        # Check if username exists in User model
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
                password=self.cleaned_data['password'] or 'Student@123',  # Default password
                first_name=self.cleaned_data['first_name'],
                last_name=self.cleaned_data['last_name'],
                role='student'
            )
        
        # Save student
        student = super().save(commit=False)
        student.user = user
        
        if self.request and hasattr(self.request, 'user'):
            student.created_by = self.request.user
        
        if commit:
            student.save()
        
        return student

class StudentSearchForm(forms.Form):
    """Form for searching students"""
    
    query = forms.CharField(max_length=100, required=False, widget=forms.TextInput(attrs={
        'placeholder': 'Search by name, admission number, or KCPE index...',
        'class': 'form-control'
    }))
    
    class_level = forms.ChoiceField(choices=[('', 'All Classes')] + Student.CLASS_LEVELS, required=False)
    stream = forms.ChoiceField(choices=[('', 'All Streams')] + Student.STREAMS, required=False)
    gender = forms.ChoiceField(choices=[('', 'All Genders')] + Student.GENDER_CHOICES, required=False)
    is_active = forms.BooleanField(required=False, initial=True, widget=forms.CheckboxInput(attrs={
        'class': 'form-check-input'
    }))

class StudentBulkUploadForm(forms.Form):
    """Form for bulk uploading students via CSV"""
    
    csv_file = forms.FileField(label='CSV File', help_text='Upload a CSV file with student data')
    
    def clean_csv_file(self):
        file = self.cleaned_data['csv_file']
        if not file.name.endswith('.csv'):
            raise ValidationError('Please upload a CSV file.')
        return file

class ParentForm(forms.ModelForm):
    """Form for creating/editing parents"""
    
    class Meta:
        model = Parent
        fields = '__all__'
        widgets = {
            'physical_address': forms.Textarea(attrs={'rows': 2}),
            'work_address': forms.Textarea(attrs={'rows': 2}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['alternative_phone'].required = False
        self.fields['email'].required = False
        self.fields['occupation'].required = False
        self.fields['employer'].required = False
        self.fields['work_address'].required = False
        self.fields['physical_address'].required = False
        self.fields['postal_address'].required = False

class StudentDocumentForm(forms.ModelForm):
    """Form for uploading student documents"""
    
    class Meta:
        model = StudentDocument
        fields = ['document_type', 'title', 'file', 'description']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['description'].required = False

class ClubForm(forms.ModelForm):
    """Form for creating/editing clubs"""
    
    class Meta:
        model = Club
        fields = '__all__'
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['patron'].required = False
        self.fields['chairperson'].required = False
        self.fields['secretary'].required = False
        self.fields['treasurer'].required = False
        self.fields['meeting_day'].required = False
        self.fields['meeting_venue'].required = False

class SportForm(forms.ModelForm):
    """Form for creating/editing sports"""
    
    class Meta:
        model = Sport
        fields = '__all__'
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['coach'].required = False
        self.fields['captain'].required = False
        self.fields['vice_captain'].required = False
        self.fields['training_day'].required = False
        self.fields['training_venue'].required = False

class StudentNoteForm(forms.ModelForm):
    """Form for adding notes to students"""
    
    class Meta:
        model = StudentNote
        fields = ['note_type', 'title', 'content']
        widgets = {
            'content': forms.Textarea(attrs={'rows': 4}),
        }

class StudentSubjectEnrollmentForm(forms.Form):
    """Form for enrolling students in subjects"""
    
    subjects = forms.ModelMultipleChoiceField(
        queryset=Subject.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False
    )
    
    def __init__(self, *args, **kwargs):
        self.student = kwargs.pop('student', None)
        super().__init__(*args, **kwargs)
        
        if self.student:
            # Filter subjects based on student's class
            self.fields['subjects'].queryset = Subject.objects.filter(
                classes__contains=[self.student.current_class]
            )
            # Set initial to currently enrolled subjects
            self.fields['subjects'].initial = self.student.subjects.all()

class StudentFilterForm(forms.Form):
    """Advanced filter form for students"""
    
    class_level = forms.MultipleChoiceField(
        choices=Student.CLASS_LEVELS,
        widget=forms.CheckboxSelectMultiple,
        required=False
    )
    
    stream = forms.MultipleChoiceField(
        choices=Student.STREAMS,
        widget=forms.CheckboxSelectMultiple,
        required=False
    )
    
    gender = forms.ChoiceField(
        choices=[('', 'All')] + list(Student.GENDER_CHOICES),
        required=False
    )
    
    boarding_status = forms.ChoiceField(
        choices=[('', 'All')] + list(Student.BOARDING_STATUS),
        required=False
    )
    
    year_of_admission = forms.IntegerField(
        required=False,
        widget=forms.NumberInput(attrs={'placeholder': 'Year'})
    )
    
    has_outstanding_fees = forms.BooleanField(required=False)
    is_active = forms.BooleanField(required=False, initial=True)

class StudentTransferForm(forms.Form):
    """Form for transferring students between classes/streams"""
    
    new_class = forms.ChoiceField(choices=Student.CLASS_LEVELS)
    new_stream = forms.ChoiceField(choices=Student.STREAMS)
    reason = forms.CharField(widget=forms.Textarea(attrs={'rows': 3}), required=False)
    effective_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    
    def __init__(self, *args, **kwargs):
        self.student = kwargs.pop('student', None)
        super().__init__(*args, **kwargs)
        
        if self.student:
            # Remove current class/stream from choices
            self.fields['new_class'].choices = [
                (k, v) for k, v in Student.CLASS_LEVELS if k != self.student.current_class
            ]
            self.fields['new_stream'].choices = Student.STREAMS