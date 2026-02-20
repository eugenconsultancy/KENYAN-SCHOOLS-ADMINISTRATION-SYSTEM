from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.urls import reverse
from accounts.models import User
import datetime

class Student(models.Model):
    """Student model for Kenyan Secondary Schools"""
    
    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
    ]
    
    CLASS_LEVELS = [
        (1, 'Form 1'),
        (2, 'Form 2'),
        (3, 'Form 3'),
        (4, 'Form 4'),
    ]
    
    STREAMS = [
        ('East', 'East'),
        ('West', 'West'),
        ('North', 'North'),
        ('South', 'South'),
    ]
    
    BOARDING_STATUS = [
        ('boarder', 'Boarder'),
        ('day_scholar', 'Day Scholar'),
    ]
    
    # Link to User account
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='student_profile')
    
    # Personal Information
    admission_number = models.CharField(max_length=20, unique=True)
    kcpe_index = models.CharField(max_length=20, unique=True)
    kcpe_marks = models.IntegerField(validators=[MinValueValidator(0), MaxValueValidator(500)])
    date_of_birth = models.DateField()
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES)
    
    # Academic Information
    current_class = models.IntegerField(choices=CLASS_LEVELS, default=1)
    stream = models.CharField(max_length=10, choices=STREAMS, default='East')
    admission_class = models.IntegerField(choices=CLASS_LEVELS)
    year_of_admission = models.IntegerField(default=datetime.datetime.now().year)
    is_active = models.BooleanField(default=True)
    
    # Contact Information
    phone_number = models.CharField(max_length=15, blank=True)
    alternative_phone = models.CharField(max_length=15, blank=True)
    email = models.EmailField(blank=True)
    physical_address = models.TextField(blank=True)
    postal_address = models.CharField(max_length=100, blank=True)
    
    # Parent/Guardian Information
    parent_name = models.CharField(max_length=100)
    parent_phone = models.CharField(max_length=15)
    parent_email = models.EmailField(blank=True)
    parent_occupation = models.CharField(max_length=100, blank=True)
    
    # Emergency Contact
    emergency_contact_name = models.CharField(max_length=100)
    emergency_contact_phone = models.CharField(max_length=15)
    emergency_contact_relationship = models.CharField(max_length=50)
    
    # Additional Information
    boarding_status = models.CharField(max_length=20, choices=BOARDING_STATUS, default='day_scholar')
    medical_conditions = models.TextField(blank=True, help_text="Any medical conditions or allergies")
    previous_school = models.CharField(max_length=200, blank=True)
    notes = models.TextField(blank=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_students')
    
    class Meta:
        ordering = ['current_class', 'stream', 'admission_number']
        indexes = [
            models.Index(fields=['admission_number']),
            models.Index(fields=['kcpe_index']),
            models.Index(fields=['current_class', 'stream']),
        ]
        verbose_name = 'Student'
        verbose_name_plural = 'Students'
    
    def __str__(self):
        return f"{self.admission_number} - {self.user.get_full_name()} (Form {self.current_class} {self.stream})"
    
    def get_absolute_url(self):
        return reverse('students:detail', args=[self.id])
    
    def get_full_name(self):
        return self.user.get_full_name()
    
    def get_age(self):
        today = datetime.date.today()
        return today.year - self.date_of_birth.year - ((today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day))
    
    def get_current_class_name(self):
        return f"Form {self.current_class} {self.stream}"
    
    @property
    def username(self):
        return self.user.username
    
    @property
    def email(self):
        return self.user.email

class Parent(models.Model):
    """Parent/Guardian model"""
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True, related_name='parent_profile')
    students = models.ManyToManyField(Student, related_name='parents')
    
    # Personal Information
    full_name = models.CharField(max_length=100)
    relationship = models.CharField(max_length=50)  # Father, Mother, Guardian, etc.
    phone_number = models.CharField(max_length=15)
    alternative_phone = models.CharField(max_length=15, blank=True)
    email = models.EmailField(blank=True)
    
    # Professional Information
    occupation = models.CharField(max_length=100, blank=True)
    employer = models.CharField(max_length=200, blank=True)
    work_address = models.TextField(blank=True)
    
    # Address
    physical_address = models.TextField(blank=True)
    postal_address = models.CharField(max_length=100, blank=True)
    
    # Emergency Contact (if different from parent)
    emergency_contact = models.BooleanField(default=False)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['full_name']
        verbose_name = 'Parent'
        verbose_name_plural = 'Parents'
    
    def __str__(self):
        return f"{self.full_name} - {self.relationship}"

class StudentDocument(models.Model):
    """Documents uploaded for students"""
    
    DOCUMENT_TYPES = [
        ('birth_cert', 'Birth Certificate'),
        ('kcpe_cert', 'KCPE Certificate'),
        ('passport', 'Passport Photo'),
        ('report', 'Previous Report'),
        ('medical', 'Medical Records'),
        ('other', 'Other'),
    ]
    
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='documents')
    document_type = models.CharField(max_length=20, choices=DOCUMENT_TYPES)
    title = models.CharField(max_length=100)
    file = models.FileField(upload_to='students/documents/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    description = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-uploaded_at']
    
    def __str__(self):
        return f"{self.student.admission_number} - {self.title}"

class Club(models.Model):
    """Clubs and societies in the school"""
    
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    patron = models.ForeignKey('teachers.Teacher', on_delete=models.SET_NULL, null=True, blank=True, related_name='patron_clubs')
    chairperson = models.ForeignKey(Student, on_delete=models.SET_NULL, null=True, blank=True, related_name='chaired_clubs')
    secretary = models.ForeignKey(Student, on_delete=models.SET_NULL, null=True, blank=True, related_name='secretary_clubs')
    treasurer = models.ForeignKey(Student, on_delete=models.SET_NULL, null=True, blank=True, related_name='treasurer_clubs')
    meeting_day = models.CharField(max_length=20, blank=True, help_text="e.g., Monday 4:00 PM")
    meeting_venue = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # ManyToMany relationship with students
    members = models.ManyToManyField(Student, through='ClubMembership', related_name='clubs')
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return self.name
    
    def get_member_count(self):
        return self.members.count()

class ClubMembership(models.Model):
    """Track student memberships in clubs with roles"""
    
    POSITION_CHOICES = [
        ('member', 'Member'),
        ('chairperson', 'Chairperson'),
        ('vice_chair', 'Vice Chairperson'),
        ('secretary', 'Secretary'),
        ('treasurer', 'Treasurer'),
        ('organizing_secretary', 'Organizing Secretary'),
    ]
    
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    club = models.ForeignKey(Club, on_delete=models.CASCADE)
    position = models.CharField(max_length=20, choices=POSITION_CHOICES, default='member')
    joined_date = models.DateField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        unique_together = ['student', 'club']
        ordering = ['club', 'position']
    
    def __str__(self):
        return f"{self.student.get_full_name()} - {self.club.name} ({self.get_position_display()})"

class Sport(models.Model):
    """Sports activities in the school"""
    
    SPORT_CATEGORIES = [
        ('ball', 'Ball Games'),
        ('athletics', 'Athletics'),
        ('racquet', 'Racquet Sports'),
        ('combat', 'Combat Sports'),
        ('water', 'Water Sports'),
        ('other', 'Other'),
    ]
    
    name = models.CharField(max_length=100, unique=True)
    category = models.CharField(max_length=20, choices=SPORT_CATEGORIES)
    description = models.TextField(blank=True)
    coach = models.ForeignKey('teachers.Teacher', on_delete=models.SET_NULL, null=True, blank=True, related_name='coached_sports')
    captain = models.ForeignKey(Student, on_delete=models.SET_NULL, null=True, blank=True, related_name='captained_sports')
    vice_captain = models.ForeignKey(Student, on_delete=models.SET_NULL, null=True, blank=True, related_name='vice_captained_sports')
    training_day = models.CharField(max_length=20, blank=True)
    training_venue = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)
    
    # ManyToMany relationship with students
    players = models.ManyToManyField(Student, through='SportParticipation', related_name='sports')
    
    class Meta:
        ordering = ['category', 'name']
    
    def __str__(self):
        return self.name
    
    def get_player_count(self):
        return self.players.count()

class SportParticipation(models.Model):
    """Track student participation in sports with positions"""
    
    POSITION_CHOICES = [
        ('player', 'Player'),
        ('captain', 'Captain'),
        ('vice_captain', 'Vice Captain'),
        ('reserve', 'Reserve'),
    ]
    
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    sport = models.ForeignKey(Sport, on_delete=models.CASCADE)
    position = models.CharField(max_length=20, choices=POSITION_CHOICES, default='player')
    joined_date = models.DateField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        unique_together = ['student', 'sport']
        ordering = ['sport', 'position']
    
    def __str__(self):
        return f"{self.student.get_full_name()} - {self.sport.name} ({self.get_position_display()})"

class StudentNote(models.Model):
    """Notes about students (behavior, achievements, etc.)"""
    
    NOTE_TYPES = [
        ('academic', 'Academic'),
        ('behavior', 'Behavior'),
        ('achievement', 'Achievement'),
        ('disciplinary', 'Disciplinary'),
        ('medical', 'Medical'),
        ('general', 'General'),
    ]
    
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='student_notes')
    note_type = models.CharField(max_length=20, choices=NOTE_TYPES, default='general')
    title = models.CharField(max_length=200)
    content = models.TextField()
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.student.admission_number} - {self.title}"

class Sibling(models.Model):
    """Track siblings within the school"""
    
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='sibling_relations')
    sibling = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='sibling_of')
    relationship = models.CharField(max_length=50, blank=True, help_text="e.g., Brother, Sister, etc.")
    
    class Meta:
        unique_together = ['student', 'sibling']
        verbose_name = 'Sibling'
        verbose_name_plural = 'Siblings'
    
    def __str__(self):
        return f"{self.student.get_full_name()} - {self.sibling.get_full_name()}"