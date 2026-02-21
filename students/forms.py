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
        exclude = ['user', 'created_by', 'created_at', 'updated_at', 'subjects']  # Added 'subjects' to exclude
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date', 'class': 'glass-input'}),
            'medical_conditions': forms.Textarea(attrs={'rows': 3, 'class': 'glass-input'}),
            'notes': forms.Textarea(attrs={'rows': 3, 'class': 'glass-input'}),
            'physical_address': forms.Textarea(attrs={'rows': 2, 'class': 'glass-input'}),
            'admission_number': forms.TextInput(attrs={'class': 'glass-input'}),
            'kcpe_index': forms.TextInput(attrs={'class': 'glass-input'}),
            'kcpe_marks': forms.NumberInput(attrs={'class': 'glass-input'}),
            'gender': forms.Select(attrs={'class': 'glass-input'}),
            'current_class': forms.Select(attrs={'class': 'glass-input'}),
            'stream': forms.Select(attrs={'class': 'glass-input'}),
            'admission_class': forms.Select(attrs={'class': 'glass-input'}),
            'year_of_admission': forms.NumberInput(attrs={'class': 'glass-input'}),
            'phone_number': forms.TextInput(attrs={'class': 'glass-input'}),
            'alternative_phone': forms.TextInput(attrs={'class': 'glass-input'}),
            'email': forms.EmailInput(attrs={'class': 'glass-input'}),
            'postal_address': forms.TextInput(attrs={'class': 'glass-input'}),
            'parent_name': forms.TextInput(attrs={'class': 'glass-input'}),
            'parent_phone': forms.TextInput(attrs={'class': 'glass-input'}),
            'parent_email': forms.EmailInput(attrs={'class': 'glass-input'}),
            'parent_occupation': forms.TextInput(attrs={'class': 'glass-input'}),
            'emergency_contact_name': forms.TextInput(attrs={'class': 'glass-input'}),
            'emergency_contact_phone': forms.TextInput(attrs={'class': 'glass-input'}),
            'emergency_contact_relationship': forms.TextInput(attrs={'class': 'glass-input'}),
            'boarding_status': forms.Select(attrs={'class': 'glass-input'}),
            'previous_school': forms.TextInput(attrs={'class': 'glass-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        
        print("\n" + "="*60)
        print("STUDENT FORM INIT - DEBUG")
        print("="*60)
        print(f"Instance PK: {self.instance.pk}")
        print(f"Is new instance: {self.instance.pk is None}")
        print(f"Form is bound: {self.is_bound}")
        
        # Make fields optional/required as needed
        self.fields['alternative_phone'].required = False
        self.fields['physical_address'].required = False
        self.fields['postal_address'].required = False
        self.fields['parent_occupation'].required = False
        self.fields['parent_email'].required = False
        self.fields['medical_conditions'].required = False
        self.fields['previous_school'].required = False
        self.fields['notes'].required = False
        
        # Email is required for user creation
        self.fields['email'].required = True
        
        # If editing, populate user fields
        if self.instance and self.instance.pk:
            print("MODE: EDITING existing student")
            if hasattr(self.instance, 'user') and self.instance.user:
                self.fields['username'].initial = self.instance.user.username
                self.fields['email'].initial = self.instance.user.email
                self.fields['first_name'].initial = self.instance.user.first_name
                self.fields['last_name'].initial = self.instance.user.last_name
            self.fields['password'].required = False
            self.fields['password'].help_text = "Leave blank to keep current password"
        else:
            print("MODE: CREATING new student")
            self.fields['password'].required = True
            self.fields['password'].help_text = "Required. Enter a password for the student"
    
    def clean_admission_number(self):
        admission_number = self.cleaned_data.get('admission_number')
        if not admission_number:
            raise ValidationError('Admission number is required.')
        
        # Check if admission number already exists (excluding current instance)
        if Student.objects.filter(admission_number=admission_number).exclude(pk=self.instance.pk).exists():
            raise ValidationError('A student with this admission number already exists.')
        return admission_number
    
    def clean_kcpe_index(self):
        kcpe_index = self.cleaned_data.get('kcpe_index')
        if not kcpe_index:
            raise ValidationError('KCPE index is required.')
            
        if Student.objects.filter(kcpe_index=kcpe_index).exclude(pk=self.instance.pk).exists():
            raise ValidationError('A student with this KCPE index already exists.')
        return kcpe_index
    
    def clean_kcpe_marks(self):
        kcpe_marks = self.cleaned_data.get('kcpe_marks')
        if kcpe_marks is None:
            raise ValidationError('KCPE marks is required.')
        if kcpe_marks < 0 or kcpe_marks > 500:
            raise ValidationError('KCPE marks must be between 0 and 500.')
        return kcpe_marks
    
    def clean_date_of_birth(self):
        dob = self.cleaned_data.get('date_of_birth')
        if not dob:
            raise ValidationError('Date of birth is required.')
            
        age = datetime.date.today().year - dob.year
        if age < 10 or age > 25:
            raise ValidationError('Student age must be between 10 and 25 years.')
        return dob
    
    def clean_gender(self):
        gender = self.cleaned_data.get('gender')
        if not gender:
            raise ValidationError('Gender is required.')
        return gender
    
    def clean_current_class(self):
        current_class = self.cleaned_data.get('current_class')
        if not current_class:
            raise ValidationError('Current class is required.')
        return current_class
    
    def clean_stream(self):
        stream = self.cleaned_data.get('stream')
        if not stream:
            raise ValidationError('Stream is required.')
        return stream
    
    def clean_admission_class(self):
        admission_class = self.cleaned_data.get('admission_class')
        if not admission_class:
            raise ValidationError('Admission class is required.')
        return admission_class
    
    def clean_parent_name(self):
        parent_name = self.cleaned_data.get('parent_name')
        if not parent_name:
            raise ValidationError('Parent name is required.')
        return parent_name
    
    def clean_parent_phone(self):
        parent_phone = self.cleaned_data.get('parent_phone')
        if not parent_phone:
            raise ValidationError('Parent phone is required.')
        return parent_phone
    
    def clean_emergency_contact_name(self):
        emergency_name = self.cleaned_data.get('emergency_contact_name')
        if not emergency_name:
            raise ValidationError('Emergency contact name is required.')
        return emergency_name
    
    def clean_emergency_contact_phone(self):
        emergency_phone = self.cleaned_data.get('emergency_contact_phone')
        if not emergency_phone:
            raise ValidationError('Emergency contact phone is required.')
        return emergency_phone
    
    def clean_emergency_contact_relationship(self):
        relationship = self.cleaned_data.get('emergency_contact_relationship')
        if not relationship:
            raise ValidationError('Emergency contact relationship is required.')
        return relationship
    
    def clean_username(self):
        username = self.cleaned_data.get('username')
        if not username:
            raise ValidationError('Username is required.')
            
        # Check if username exists in User model
        if self.instance.pk:
            # Editing existing student
            if User.objects.filter(username=username).exclude(pk=self.instance.user.pk).exists():
                raise ValidationError('This username is already taken.')
        else:
            # Creating new student
            if User.objects.filter(username=username).exists():
                raise ValidationError('This username is already taken.')
        return username
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if not email:
            raise ValidationError('Email is required.')
            
        if self.instance.pk:
            # Editing
            if User.objects.filter(email=email).exclude(pk=self.instance.user.pk).exists():
                raise ValidationError('This email is already registered.')
        else:
            # New
            if User.objects.filter(email=email).exists():
                raise ValidationError('This email is already registered.')
        return email
    
    def clean_first_name(self):
        first_name = self.cleaned_data.get('first_name')
        if not first_name:
            raise ValidationError('First name is required.')
        return first_name
    
    def clean_last_name(self):
        last_name = self.cleaned_data.get('last_name')
        if not last_name:
            raise ValidationError('Last name is required.')
        return last_name
    
    def clean(self):
        cleaned_data = super().clean()
        print("\n--- STUDENT FORM CLEAN METHOD ---")
        print(f"Instance PK: {self.instance.pk}")
        print(f"Cleaned data keys: {list(cleaned_data.keys())}")
        
        # Check for password on new instances
        if self.instance.pk is None and not cleaned_data.get('password'):
            self.add_error('password', 'Password is required for new students.')
            print("  ✗ Password missing for new student")
        
        # Check all required fields
        required_fields = [
            'username', 'email', 'first_name', 'last_name',
            'admission_number', 'kcpe_index', 'kcpe_marks',
            'date_of_birth', 'gender', 'current_class', 'stream',
            'admission_class', 'parent_name', 'parent_phone',
            'emergency_contact_name', 'emergency_contact_phone',
            'emergency_contact_relationship'
        ]
        
        for field in required_fields:
            if field not in cleaned_data or not cleaned_data.get(field):
                print(f"  ✗ Missing required field: {field}")
                # Don't add error here as individual field clean methods already handle it
        
        return cleaned_data
    
    def save(self, commit=True):
        print("\n" + "="*60)
        print("STUDENT FORM SAVE METHOD")
        print("="*60)
        print(f"Instance PK before save: {self.instance.pk}")
        print(f"Commit: {commit}")
        
        # Handle user account
        if self.instance.pk:
            # Update existing user
            print("MODE: UPDATE existing student")
            user = self.instance.user
            user.username = self.cleaned_data['username']
            user.email = self.cleaned_data['email']
            user.first_name = self.cleaned_data['first_name']
            user.last_name = self.cleaned_data['last_name']
            if self.cleaned_data.get('password'):
                print("  Updating password")
                user.set_password(self.cleaned_data['password'])
            user.save()
            print(f"  User updated: {user.username} (ID: {user.id})")
        else:
            # Create new user
            print("MODE: CREATE new student")
            password = self.cleaned_data.get('password')
            if not password:
                raise ValidationError('Password is required for new students.')
            
            user = User.objects.create_user(
                username=self.cleaned_data['username'],
                email=self.cleaned_data['email'],
                password=password,
                first_name=self.cleaned_data['first_name'],
                last_name=self.cleaned_data['last_name'],
                role='student'
            )
            print(f"  User created: {user.username} (ID: {user.id})")
        
        # Save student
        student = super().save(commit=False)
        student.user = user
        
        if self.request and hasattr(self.request, 'user'):
            student.created_by = self.request.user
            print(f"  Created by: {self.request.user.username}")
        
        if commit:
            student.save()
            print(f"  Student saved with ID: {student.id}")
            print(f"  Admission number: {student.admission_number}")
        
        print("="*60)
        return student

class StudentSearchForm(forms.Form):
    """Form for searching students"""
    
    query = forms.CharField(max_length=100, required=False, widget=forms.TextInput(attrs={
        'placeholder': 'Search by name, admission number, or KCPE index...',
        'class': 'glass-input'
    }))
    
    class_level = forms.ChoiceField(choices=[('', 'All Classes')] + Student.CLASS_LEVELS, required=False,
                                   widget=forms.Select(attrs={'class': 'glass-input'}))
    stream = forms.ChoiceField(choices=[('', 'All Streams')] + Student.STREAMS, required=False,
                              widget=forms.Select(attrs={'class': 'glass-input'}))
    gender = forms.ChoiceField(choices=[('', 'All Genders')] + Student.GENDER_CHOICES, required=False,
                              widget=forms.Select(attrs={'class': 'glass-input'}))
    is_active = forms.BooleanField(required=False, initial=True, widget=forms.CheckboxInput(attrs={
        'class': 'form-check-input'
    }))

class StudentBulkUploadForm(forms.Form):
    """Form for bulk uploading students via CSV"""
    
    csv_file = forms.FileField(label='CSV File', help_text='Upload a CSV file with student data',
                               widget=forms.FileInput(attrs={'class': 'glass-input'}))
    
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
            'physical_address': forms.Textarea(attrs={'rows': 2, 'class': 'glass-input'}),
            'work_address': forms.Textarea(attrs={'rows': 2, 'class': 'glass-input'}),
            'full_name': forms.TextInput(attrs={'class': 'glass-input'}),
            'relationship': forms.TextInput(attrs={'class': 'glass-input'}),
            'phone_number': forms.TextInput(attrs={'class': 'glass-input'}),
            'alternative_phone': forms.TextInput(attrs={'class': 'glass-input'}),
            'email': forms.EmailInput(attrs={'class': 'glass-input'}),
            'occupation': forms.TextInput(attrs={'class': 'glass-input'}),
            'employer': forms.TextInput(attrs={'class': 'glass-input'}),
            'postal_address': forms.TextInput(attrs={'class': 'glass-input'}),
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
            'document_type': forms.Select(attrs={'class': 'glass-input'}),
            'title': forms.TextInput(attrs={'class': 'glass-input', 'placeholder': 'Enter document title'}),
            'file': forms.FileInput(attrs={'class': 'glass-input'}),
            'description': forms.Textarea(attrs={'rows': 3, 'class': 'glass-input', 'placeholder': 'Optional description'}),
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
            'name': forms.TextInput(attrs={'class': 'glass-input'}),
            'description': forms.Textarea(attrs={'rows': 3, 'class': 'glass-input'}),
            'patron': forms.Select(attrs={'class': 'glass-input'}),
            'chairperson': forms.Select(attrs={'class': 'glass-input'}),
            'secretary': forms.Select(attrs={'class': 'glass-input'}),
            'treasurer': forms.Select(attrs={'class': 'glass-input'}),
            'meeting_day': forms.TextInput(attrs={'class': 'glass-input', 'placeholder': 'e.g., Monday 4:00 PM'}),
            'meeting_venue': forms.TextInput(attrs={'class': 'glass-input'}),
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
            'name': forms.TextInput(attrs={'class': 'glass-input'}),
            'category': forms.Select(attrs={'class': 'glass-input'}),
            'description': forms.Textarea(attrs={'rows': 3, 'class': 'glass-input'}),
            'coach': forms.Select(attrs={'class': 'glass-input'}),
            'captain': forms.Select(attrs={'class': 'glass-input'}),
            'vice_captain': forms.Select(attrs={'class': 'glass-input'}),
            'training_day': forms.TextInput(attrs={'class': 'glass-input', 'placeholder': 'e.g., Tuesday 4:00 PM'}),
            'training_venue': forms.TextInput(attrs={'class': 'glass-input'}),
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
            'note_type': forms.Select(attrs={'class': 'glass-input'}),
            'title': forms.TextInput(attrs={'class': 'glass-input', 'placeholder': 'Note title'}),
            'content': forms.Textarea(attrs={'rows': 4, 'class': 'glass-input', 'placeholder': 'Note content'}),
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
                classes__contains=[self.student.current_class],
                is_active=True
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
        required=False,
        widget=forms.Select(attrs={'class': 'glass-input'})
    )
    
    boarding_status = forms.ChoiceField(
        choices=[('', 'All')] + list(Student.BOARDING_STATUS),
        required=False,
        widget=forms.Select(attrs={'class': 'glass-input'})
    )
    
    year_of_admission = forms.IntegerField(
        required=False,
        widget=forms.NumberInput(attrs={'class': 'glass-input', 'placeholder': 'Year'})
    )
    
    has_outstanding_fees = forms.BooleanField(required=False)
    is_active = forms.BooleanField(required=False, initial=True)

class StudentTransferForm(forms.Form):
    """Form for transferring students between classes/streams"""
    
    new_class = forms.ChoiceField(choices=Student.CLASS_LEVELS, widget=forms.Select(attrs={'class': 'glass-input'}))
    new_stream = forms.ChoiceField(choices=Student.STREAMS, widget=forms.Select(attrs={'class': 'glass-input'}))
    reason = forms.CharField(widget=forms.Textarea(attrs={'rows': 3, 'class': 'glass-input'}), required=False)
    effective_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date', 'class': 'glass-input'}))
    
    def __init__(self, *args, **kwargs):
        self.student = kwargs.pop('student', None)
        super().__init__(*args, **kwargs)
        
        if self.student:
            # Remove current class/stream from choices
            self.fields['new_class'].choices = [
                (k, v) for k, v in Student.CLASS_LEVELS if k != self.student.current_class
            ]
            self.fields['new_stream'].choices = Student.STREAMS