from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.urls import reverse
from accounts.models import User
# Remove direct import of Subject and Class - will use string references
import datetime

class Teacher(models.Model):
    """Teacher model for Kenyan Schools System"""
    
    EMPLOYMENT_TYPES = [
        ('permanent', 'Permanent'),
        ('contract', 'Contract'),
        ('intern', 'Intern'),
        ('part_time', 'Part Time'),
        ('visiting', 'Visiting'),
    ]
    
    QUALIFICATION_LEVELS = [
        ('certificate', 'Certificate'),
        ('diploma', 'Diploma'),
        ('bachelors', "Bachelor's Degree"),
        ('masters', "Master's Degree"),
        ('phd', 'PhD'),
        ('other', 'Other'),
    ]
    
    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
    ]
    
    MARITAL_STATUS = [
        ('single', 'Single'),
        ('married', 'Married'),
        ('divorced', 'Divorced'),
        ('widowed', 'Widowed'),
    ]
    
    # Link to User account
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='teacher_profile')
    
    # Personal Information
    employee_number = models.CharField(max_length=20, unique=True)
    tsc_number = models.CharField(max_length=20, unique=True, verbose_name="TSC Number")
    id_number = models.CharField(max_length=10, unique=True, verbose_name="National ID")
    date_of_birth = models.DateField()
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES)
    marital_status = models.CharField(max_length=20, choices=MARITAL_STATUS, default='single')
    
    # Professional Information
    qualification_level = models.CharField(max_length=20, choices=QUALIFICATION_LEVELS)
    qualifications = models.TextField(help_text="List your qualifications and certifications")
    specialization = models.CharField(max_length=200, blank=True, help_text="Area of specialization")
    years_of_experience = models.IntegerField(default=0)
    date_employed = models.DateField()
    employment_type = models.CharField(max_length=20, choices=EMPLOYMENT_TYPES, default='permanent')
    is_active = models.BooleanField(default=True)
    
    # Contact Information
    phone_number = models.CharField(max_length=15)
    alternative_phone = models.CharField(max_length=15, blank=True)
    email = models.EmailField()
    physical_address = models.TextField(blank=True)
    postal_address = models.CharField(max_length=100, blank=True)
    
    # Emergency Contact
    emergency_contact_name = models.CharField(max_length=100)
    emergency_contact_phone = models.CharField(max_length=15)
    emergency_contact_relationship = models.CharField(max_length=50)
    
    # Bank Details
    bank_name = models.CharField(max_length=100, blank=True)
    bank_branch = models.CharField(max_length=100, blank=True)
    bank_account = models.CharField(max_length=50, blank=True)
    bank_code = models.CharField(max_length=10, blank=True)
    
    # Medical Information
    blood_group = models.CharField(max_length=5, blank=True)
    medical_conditions = models.TextField(blank=True)
    
    # Documents
    cv = models.FileField(upload_to='teachers/cv/', null=True, blank=True)
    contract = models.FileField(upload_to='teachers/contracts/', null=True, blank=True)
    passport_photo = models.ImageField(upload_to='teachers/photos/', null=True, blank=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_teachers')
    
    class Meta:
        ordering = ['user__first_name', 'user__last_name']
        indexes = [
            models.Index(fields=['employee_number']),
            models.Index(fields=['tsc_number']),
            models.Index(fields=['id_number']),
        ]
        verbose_name = 'Teacher'
        verbose_name_plural = 'Teachers'
    
    def __str__(self):
        return f"{self.employee_number} - {self.user.get_full_name()}"
    
    def get_absolute_url(self):
        return reverse('teachers:detail', args=[self.id])
    
    def get_full_name(self):
        return self.user.get_full_name()
    
    def get_age(self):
        today = datetime.date.today()
        return today.year - self.date_of_birth.year - ((today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day))
    
    @property
    def username(self):
        return self.user.username

class TeacherQualification(models.Model):
    """Additional qualifications for teachers"""
    
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE, related_name='additional_qualifications')
    qualification = models.CharField(max_length=200)
    institution = models.CharField(max_length=200)
    year_obtained = models.IntegerField()
    certificate = models.FileField(upload_to='teachers/qualifications/', null=True, blank=True)
    
    class Meta:
        ordering = ['-year_obtained']
    
    def __str__(self):
        return f"{self.teacher.get_full_name()} - {self.qualification}"

class TeacherSubject(models.Model):
    """Subjects taught by teachers"""
    
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE, related_name='subjects_taught')
    # Use string reference to avoid circular import
    subject = models.ForeignKey('academics.Subject', on_delete=models.CASCADE, related_name='teachers')
    is_main = models.BooleanField(default=False, help_text="Main teaching subject")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['teacher', 'subject']
        ordering = ['-is_main', 'subject__name']
    
    def __str__(self):
        return f"{self.teacher.get_full_name()} - {self.subject.name}"

class TeacherClass(models.Model):
    """Classes assigned to teachers (form teachers)"""
    
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE, related_name='form_classes')
    class_level = models.IntegerField(choices=[(1, 'Form 1'), (2, 'Form 2'), (3, 'Form 3'), (4, 'Form 4')])
    stream = models.CharField(max_length=10, choices=[('East', 'East'), ('West', 'West'), ('North', 'North'), ('South', 'South')])
    # Use string reference to avoid circular import
    academic_year = models.ForeignKey('academics.AcademicYear', on_delete=models.CASCADE)
    is_current = models.BooleanField(default=True)
    assigned_date = models.DateField(auto_now_add=True)
    
    class Meta:
        unique_together = ['class_level', 'stream', 'academic_year']
        ordering = ['-academic_year', 'class_level', 'stream']
    
    def __str__(self):
        return f"{self.teacher.get_full_name()} - Form {self.class_level} {self.stream} ({self.academic_year})"

class TeacherLeave(models.Model):
    """Teacher leave records"""
    
    LEAVE_TYPES = [
        ('annual', 'Annual Leave'),
        ('sick', 'Sick Leave'),
        ('maternity', 'Maternity Leave'),
        ('paternity', 'Paternity Leave'),
        ('compassionate', 'Compassionate Leave'),
        ('study', 'Study Leave'),
        ('unpaid', 'Unpaid Leave'),
        ('other', 'Other'),
    ]
    
    LEAVE_STATUS = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
    ]
    
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE, related_name='leaves')
    leave_type = models.CharField(max_length=20, choices=LEAVE_TYPES)
    start_date = models.DateField()
    end_date = models.DateField()
    days_requested = models.IntegerField()
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=LEAVE_STATUS, default='pending')
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='approved_leaves')
    approved_date = models.DateTimeField(null=True, blank=True)
    remarks = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.teacher.get_full_name()} - {self.get_leave_type_display()} ({self.start_date} to {self.end_date})"
    
    def save(self, *args, **kwargs):
        if not self.days_requested:
            self.days_requested = (self.end_date - self.start_date).days + 1
        super().save(*args, **kwargs)

class TeacherAttendance(models.Model):
    """Teacher attendance tracking"""
    
    ATTENDANCE_STATUS = [
        ('present', 'Present'),
        ('absent', 'Absent'),
        ('late', 'Late'),
        ('half_day', 'Half Day'),
        ('leave', 'On Leave'),
        ('official', 'Official Duty'),
    ]
    
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE, related_name='teacher_attendance_records')
    date = models.DateField()
    status = models.CharField(max_length=20, choices=ATTENDANCE_STATUS, default='present')
    check_in_time = models.TimeField(null=True, blank=True)
    check_out_time = models.TimeField(null=True, blank=True)
    late_minutes = models.IntegerField(default=0)
    remarks = models.CharField(max_length=200, blank=True)
    marked_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='teacher_attendance_marked')
    
    class Meta:
        unique_together = ['teacher', 'date']
        ordering = ['-date']
    
    def __str__(self):
        return f"{self.teacher.get_full_name()} - {self.date} - {self.get_status_display()}"

class TeacherDocument(models.Model):
    """Documents for teachers"""
    
    DOCUMENT_TYPES = [
        ('id', 'National ID'),
        ('tsc', 'TSC Certificate'),
        ('degree', 'Degree Certificate'),
        ('diploma', 'Diploma Certificate'),
        ('certificate', 'Other Certificate'),
        ('cv', 'Curriculum Vitae'),
        ('contract', 'Employment Contract'),
        ('payslip', 'Payslip'),
        ('other', 'Other'),
    ]
    
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE, related_name='documents')
    document_type = models.CharField(max_length=20, choices=DOCUMENT_TYPES)
    title = models.CharField(max_length=100)
    file = models.FileField(upload_to='teachers/documents/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    description = models.TextField(blank=True)
    expiry_date = models.DateField(null=True, blank=True, help_text="For documents that expire")
    
    class Meta:
        ordering = ['-uploaded_at']
    
    def __str__(self):
        return f"{self.teacher.get_full_name()} - {self.title}"

class TeacherPerformance(models.Model):
    """Teacher performance evaluation"""
    
    PERFORMANCE_RATINGS = [
        (1, 'Poor'),
        (2, 'Fair'),
        (3, 'Good'),
        (4, 'Very Good'),
        (5, 'Excellent'),
    ]
    
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE, related_name='performances')
    # Use string references to avoid circular imports
    academic_year = models.ForeignKey('academics.AcademicYear', on_delete=models.CASCADE)
    term = models.ForeignKey('academics.Term', on_delete=models.CASCADE)
    
    # Evaluation criteria
    lesson_preparation = models.IntegerField(choices=PERFORMANCE_RATINGS)
    lesson_delivery = models.IntegerField(choices=PERFORMANCE_RATINGS)
    student_assessment = models.IntegerField(choices=PERFORMANCE_RATINGS)
    class_management = models.IntegerField(choices=PERFORMANCE_RATINGS)
    punctuality = models.IntegerField(choices=PERFORMANCE_RATINGS)
    professional_conduct = models.IntegerField(choices=PERFORMANCE_RATINGS)
    co_curricular = models.IntegerField(choices=PERFORMANCE_RATINGS)
    
    comments = models.TextField(blank=True)
    evaluator = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='evaluated_teachers')
    evaluation_date = models.DateField(auto_now_add=True)
    
    class Meta:
        unique_together = ['teacher', 'term']
        ordering = ['-evaluation_date']
    
    def __str__(self):
        return f"{self.teacher.get_full_name()} - {self.term} Performance"
    
    def get_average_rating(self):
        ratings = [
            self.lesson_preparation,
            self.lesson_delivery,
            self.student_assessment,
            self.class_management,
            self.punctuality,
            self.professional_conduct,
            self.co_curricular,
        ]
        return sum(ratings) / len(ratings)

class TeacherSalary(models.Model):
    """Teacher salary records"""
    
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE, related_name='salaries')
    month = models.IntegerField(choices=[(i, i) for i in range(1, 13)])
    year = models.IntegerField()
    basic_salary = models.DecimalField(max_digits=10, decimal_places=2)
    house_allowance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    transport_allowance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    medical_allowance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    other_allowances = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Deductions
    tax = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    nhif = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    nssf = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    loan_deduction = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    other_deductions = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    net_salary = models.DecimalField(max_digits=10, decimal_places=2)
    payment_date = models.DateField()
    payment_method = models.CharField(max_length=50, default='bank_transfer')
    payslip = models.FileField(upload_to='teachers/payslips/', null=True, blank=True)
    
    class Meta:
        unique_together = ['teacher', 'month', 'year']
        ordering = ['-year', '-month']
    
    def __str__(self):
        return f"{self.teacher.get_full_name()} - {self.month}/{self.year}"
    
    def calculate_net_salary(self):
        total_allowances = self.house_allowance + self.transport_allowance + self.medical_allowance + self.other_allowances
        total_deductions = self.tax + self.nhif + self.nssf + self.loan_deduction + self.other_deductions
        gross = self.basic_salary + total_allowances
        return gross - total_deductions
    
    def save(self, *args, **kwargs):
        self.net_salary = self.calculate_net_salary()
        super().save(*args, **kwargs)

class TeacherTraining(models.Model):
    """Professional development training for teachers"""
    
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE, related_name='trainings')
    title = models.CharField(max_length=200)
    provider = models.CharField(max_length=200)
    start_date = models.DateField()
    end_date = models.DateField()
    duration_days = models.IntegerField()
    certificate = models.FileField(upload_to='teachers/trainings/', null=True, blank=True)
    description = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-end_date']
    
    def __str__(self):
        return f"{self.teacher.get_full_name()} - {self.title}"

class TeacherAward(models.Model):
    """Awards and recognition for teachers"""
    
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE, related_name='awards')
    award_name = models.CharField(max_length=200)
    awarding_body = models.CharField(max_length=200)
    date_received = models.DateField()
    description = models.TextField(blank=True)
    certificate = models.FileField(upload_to='teachers/awards/', null=True, blank=True)
    
    class Meta:
        ordering = ['-date_received']
    
    def __str__(self):
        return f"{self.teacher.get_full_name()} - {self.award_name}"

class TeacherNote(models.Model):
    """Notes about teachers"""
    
    NOTE_TYPES = [
        ('general', 'General'),
        ('performance', 'Performance'),
        ('disciplinary', 'Disciplinary'),
        ('achievement', 'Achievement'),
        ('training', 'Training Need'),
        ('other', 'Other'),
    ]
    
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE, related_name='notes')
    note_type = models.CharField(max_length=20, choices=NOTE_TYPES, default='general')
    title = models.CharField(max_length=200)
    content = models.TextField()
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.teacher.get_full_name()} - {self.title}"