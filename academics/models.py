from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.urls import reverse
# Remove direct import of Student - will query directly in methods
from accounts.models import User
import datetime

class AcademicYear(models.Model):
    """Academic year model"""
    
    name = models.CharField(max_length=20, unique=True, help_text="e.g., 2024")
    start_date = models.DateField()
    end_date = models.DateField()
    is_current = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-start_date']
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if self.is_current:
            # Set all other academic years to not current
            AcademicYear.objects.filter(is_current=True).update(is_current=False)
        super().save(*args, **kwargs)

class Term(models.Model):
    """Term model for Kenyan schools (3 terms per year)"""
    
    TERM_CHOICES = [
        (1, 'Term 1'),
        (2, 'Term 2'),
        (3, 'Term 3'),
    ]
    
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE, related_name='terms')
    term = models.IntegerField(choices=TERM_CHOICES)
    name = models.CharField(max_length=50, blank=True)
    start_date = models.DateField()
    end_date = models.DateField()
    is_current = models.BooleanField(default=False)
    closing_date = models.DateField(null=True, blank=True)
    reporting_date = models.DateField(null=True, blank=True)
    
    class Meta:
        ordering = ['academic_year', 'term']
        unique_together = ['academic_year', 'term']
    
    def __str__(self):
        return f"{self.academic_year} - {self.get_term_display()}"
    
    def save(self, *args, **kwargs):
        if not self.name:
            self.name = f"{self.academic_year} - {self.get_term_display()}"
        if self.is_current:
            # Set all other terms to not current
            Term.objects.filter(is_current=True).update(is_current=False)
        super().save(*args, **kwargs)

class SubjectCategory(models.Model):
    """Subject categories (e.g., Sciences, Humanities, etc.)"""
    
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=20, unique=True)
    description = models.TextField(blank=True)
    
    class Meta:
        verbose_name_plural = "Subject Categories"
        ordering = ['name']
    
    def __str__(self):
        return self.name

class Subject(models.Model):
    """Subject model for Kenyan curriculum"""
    
    SUBJECT_TYPES = [
        ('compulsory', 'Compulsory'),
        ('elective', 'Elective'),
        ('technical', 'Technical'),
        ('foreign', 'Foreign Language'),
    ]
    
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20, unique=True)
    category = models.ForeignKey(SubjectCategory, on_delete=models.SET_NULL, null=True, related_name='subjects')
    subject_type = models.CharField(max_length=20, choices=SUBJECT_TYPES, default='compulsory')
    
    # Which classes offer this subject
    classes = models.JSONField(default=list, help_text="List of class levels that offer this subject")
    
    # Grading configuration
    pass_mark = models.IntegerField(default=40, validators=[MinValueValidator(0), MaxValueValidator(100)])
    max_mark = models.IntegerField(default=100, validators=[MinValueValidator(0), MaxValueValidator(500)])
    
    # Subject details
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.code})"

class Class(models.Model):
    """Class level with streams"""
    
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
    
    class_level = models.IntegerField(choices=CLASS_LEVELS)
    stream = models.CharField(max_length=10, choices=STREAMS)
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE, related_name='classes')
    
    # Class teacher (form master) - use string reference
    class_teacher = models.ForeignKey('teachers.Teacher', on_delete=models.SET_NULL, null=True, related_name='class_teacher_of')
    
    # Class capacity
    capacity = models.IntegerField(default=45)
    
    # Class subjects (many-to-many through SubjectAllocation)
    subjects = models.ManyToManyField(Subject, through='SubjectAllocation', related_name='classes_offered')
    
    class Meta:
        ordering = ['class_level', 'stream']
        unique_together = ['class_level', 'stream', 'academic_year']
        verbose_name_plural = 'Classes'
    
    def __str__(self):
        return f"Form {self.class_level} {self.stream} - {self.academic_year}"
    
    def get_student_count(self):
        """
        Get the number of active students in this class by querying the Student model directly
        """
        from students.models import Student
        return Student.objects.filter(
            current_class=self.class_level,
            stream=self.stream,
            is_active=True
        ).count()
    
    def get_capacity_percentage(self):
        """
        Calculate the percentage of class capacity filled
        """
        count = self.get_student_count()
        return (count / self.capacity * 100) if self.capacity > 0 else 0

class SubjectAllocation(models.Model):
    """Allocation of subjects to classes with teachers"""
    
    class_assigned = models.ForeignKey(Class, on_delete=models.CASCADE, related_name='subject_allocations')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='class_allocations')
    # Use string reference to avoid circular import
    teacher = models.ForeignKey('teachers.Teacher', on_delete=models.SET_NULL, null=True, related_name='subject_allocations')
    
    # Weekly lessons
    lessons_per_week = models.IntegerField(default=4)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['class_assigned', 'subject']
        unique_together = ['class_assigned', 'subject']
    
    def __str__(self):
        return f"{self.class_assigned} - {self.subject.name}"

class Exam(models.Model):
    """Examination model"""
    
    EXAM_TYPES = [
        ('cat', 'Continuous Assessment Test'),
        ('midterm', 'Mid-Term Exam'),
        ('endterm', 'End of Term Exam'),
        ('mock', 'Mock Exam'),
        ('national', 'National Exam'),
    ]
    
    term = models.ForeignKey(Term, on_delete=models.CASCADE, related_name='exams')
    name = models.CharField(max_length=200)
    exam_type = models.CharField(max_length=20, choices=EXAM_TYPES)
    
    # Exam schedule
    start_date = models.DateField()
    end_date = models.DateField()
    
    # Subjects included
    subjects = models.ManyToManyField(Subject, related_name='exams')
    
    # Exam details
    description = models.TextField(blank=True)
    is_published = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    
    class Meta:
        ordering = ['-start_date']
    
    def __str__(self):
        return f"{self.name} - {self.term}"

class ExamSchedule(models.Model):
    """Detailed exam schedule"""
    
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name='schedule')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    class_assigned = models.ForeignKey(Class, on_delete=models.CASCADE)
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    venue = models.CharField(max_length=100, blank=True)
    
    class Meta:
        ordering = ['date', 'start_time']
        unique_together = ['exam', 'subject', 'class_assigned']
    
    def __str__(self):
        return f"{self.subject.name} - {self.class_assigned} - {self.date}"

class Result(models.Model):
    """Student results for exams"""
    
    GRADE_CHOICES = [
        ('A', 'A'),
        ('A-', 'A-'),
        ('B+', 'B+'),
        ('B', 'B'),
        ('B-', 'B-'),
        ('C+', 'C+'),
        ('C', 'C'),
        ('C-', 'C-'),
        ('D+', 'D+'),
        ('D', 'D'),
        ('D-', 'D-'),
        ('E', 'E'),
    ]
    
    student = models.ForeignKey('students.Student', on_delete=models.CASCADE, related_name='results')  # String reference
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name='results')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    
    marks = models.IntegerField(validators=[MinValueValidator(0), MaxValueValidator(100)])
    grade = models.CharField(max_length=2, choices=GRADE_CHOICES, blank=True)
    points = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    
    # Remarks
    remarks = models.TextField(blank=True)
    
    # Tracking
    entered_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='entered_results')
    entered_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-exam__start_date', 'subject__name']
        unique_together = ['student', 'exam', 'subject']
    
    def __str__(self):
        return f"{self.student.get_full_name()} - {self.subject.name} - {self.marks}"
    
    def save(self, *args, **kwargs):
        # Calculate grade based on marks
        self.grade = self.calculate_grade()
        # Calculate points
        self.points = self.calculate_points()
        super().save(*args, **kwargs)
    
    def calculate_grade(self):
        """Calculate grade based on Kenyan system"""
        marks = self.marks
        if marks >= 80:
            return 'A'
        elif marks >= 75:
            return 'A-'
        elif marks >= 70:
            return 'B+'
        elif marks >= 65:
            return 'B'
        elif marks >= 60:
            return 'B-'
        elif marks >= 55:
            return 'C+'
        elif marks >= 50:
            return 'C'
        elif marks >= 45:
            return 'C-'
        elif marks >= 40:
            return 'D+'
        elif marks >= 35:
            return 'D'
        elif marks >= 30:
            return 'D-'
        else:
            return 'E'
    
    def calculate_points(self):
        """Calculate grade points"""
        grade_points = {
            'A': 12, 'A-': 11, 'B+': 10, 'B': 9, 'B-': 8,
            'C+': 7, 'C': 6, 'C-': 5, 'D+': 4, 'D': 3,
            'D-': 2, 'E': 1
        }
        return grade_points.get(self.grade, 0)

class ResultSummary(models.Model):
    """Summary of student results per term"""
    
    student = models.ForeignKey('students.Student', on_delete=models.CASCADE, related_name='result_summaries')  # String reference
    term = models.ForeignKey(Term, on_delete=models.CASCADE, related_name='result_summaries')
    
    total_marks = models.IntegerField(default=0)
    average = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    mean_grade = models.CharField(max_length=2, choices=Result.GRADE_CHOICES, blank=True)
    total_points = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    
    position_in_class = models.IntegerField(null=True, blank=True)
    position_in_stream = models.IntegerField(null=True, blank=True)
    
    subjects_taken = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['term', 'position_in_class']
        unique_together = ['student', 'term']
    
    def __str__(self):
        return f"{self.student.get_full_name()} - {self.term} - Avg: {self.average}"

class Timetable(models.Model):
    """Class timetable"""
    
    DAYS_OF_WEEK = [
        (1, 'Monday'),
        (2, 'Tuesday'),
        (3, 'Wednesday'),
        (4, 'Thursday'),
        (5, 'Friday'),
    ]
    
    class_assigned = models.ForeignKey(Class, on_delete=models.CASCADE, related_name='timetables')
    term = models.ForeignKey(Term, on_delete=models.CASCADE, related_name='timetables')
    day = models.IntegerField(choices=DAYS_OF_WEEK)
    
    start_time = models.TimeField()
    end_time = models.TimeField()
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    # Use string reference to avoid circular import
    teacher = models.ForeignKey('teachers.Teacher', on_delete=models.SET_NULL, null=True)
    
    class Meta:
        ordering = ['class_assigned', 'day', 'start_time']
    
    def __str__(self):
        return f"{self.class_assigned} - {self.get_day_display()} {self.start_time}-{self.end_time}"

class LessonPlan(models.Model):
    """Teacher's lesson plans"""
    
    # Use string reference to avoid circular import
    teacher = models.ForeignKey('teachers.Teacher', on_delete=models.CASCADE, related_name='lesson_plans')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    class_assigned = models.ForeignKey(Class, on_delete=models.CASCADE)
    term = models.ForeignKey(Term, on_delete=models.CASCADE)
    
    topic = models.CharField(max_length=200)
    subtopics = models.JSONField(default=list)
    objectives = models.TextField()
    
    week = models.IntegerField()
    lesson_number = models.IntegerField()
    
    materials = models.TextField(blank=True)
    activities = models.TextField(blank=True)
    assessment = models.TextField(blank=True)
    remarks = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['term', 'week', 'lesson_number']
    
    def __str__(self):
        return f"{self.subject.name} - {self.topic} - Week {self.week}"

class Homework(models.Model):
    """Homework assignments"""
    
    # Use string reference to avoid circular import
    teacher = models.ForeignKey('teachers.Teacher', on_delete=models.CASCADE, related_name='homeworks')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    class_assigned = models.ForeignKey(Class, on_delete=models.CASCADE, related_name='homeworks')
    
    title = models.CharField(max_length=200)
    description = models.TextField()
    
    date_assigned = models.DateField(auto_now_add=True)
    due_date = models.DateField()
    
    attachments = models.FileField(upload_to='academics/homework/', null=True, blank=True)
    
    is_submitted = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-due_date']
    
    def __str__(self):
        return f"{self.subject.name} - {self.title} - Due: {self.due_date}"

class HomeworkSubmission(models.Model):
    """Student homework submissions"""
    
    homework = models.ForeignKey(Homework, on_delete=models.CASCADE, related_name='submissions')
    student = models.ForeignKey('students.Student', on_delete=models.CASCADE, related_name='homework_submissions')  # String reference
    
    submission_date = models.DateTimeField(auto_now_add=True)
    content = models.TextField(blank=True)
    attachment = models.FileField(upload_to='academics/submissions/', null=True, blank=True)
    
    marks = models.IntegerField(null=True, blank=True)
    feedback = models.TextField(blank=True)
    graded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    graded_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-submission_date']
        unique_together = ['homework', 'student']
    
    def __str__(self):
        return f"{self.student.get_full_name()} - {self.homework.title}"