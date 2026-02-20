import csv
import io
from django.core.files.storage import default_storage
from .models import Student
from accounts.models import User
import datetime


def generate_admission_number():
    """Generate a unique admission number"""
    last_student = Student.objects.order_by('-id').first()
    if last_student:
        last_number = int(last_student.admission_number.split('/')[-1])
        new_number = last_number + 1
    else:
        new_number = 1001  # Starting number
    
    year = datetime.now().year
    return f"ADM/{year}/{new_number:04d}"

def generate_kcpe_index():
    """Generate a unique KCPE index number"""
    import random
    year = random.randint(2015, 2023)
    center_code = random.randint(100, 999)
    candidate_number = random.randint(1000, 9999)
    return f"{year}/{center_code}/{candidate_number:04d}"

def parse_student_csv(csv_content):
    """Parse CSV content and return list of student data"""
    data = []
    csv_file = io.StringIO(csv_content)
    reader = csv.DictReader(csv_file)
    
    for row in reader:
        # Validate required fields
        required_fields = ['first_name', 'last_name', 'admission_number', 
                          'kcpe_index', 'gender', 'current_class']
        
        missing = [field for field in required_fields if not row.get(field)]
        if missing:
            raise ValueError(f"Missing required fields: {', '.join(missing)}")
        
        data.append({
            'first_name': row['first_name'],
            'last_name': row['last_name'],
            'username': row.get('username', row['admission_number'].lower()),
            'email': row.get('email', ''),
            'admission_number': row['admission_number'],
            'kcpe_index': row['kcpe_index'],
            'kcpe_marks': int(row.get('kcpe_marks', 0)),
            'date_of_birth': row.get('date_of_birth', '2000-01-01'),
            'gender': row['gender'],
            'current_class': int(row['current_class']),
            'stream': row.get('stream', 'East'),
            'admission_class': int(row.get('admission_class', row['current_class'])),
            'year_of_admission': int(row.get('year_of_admission', datetime.now().year)),
            'parent_name': row.get('parent_name', ''),
            'parent_phone': row.get('parent_phone', ''),
            'emergency_contact_name': row.get('emergency_contact_name', ''),
            'emergency_contact_phone': row.get('emergency_contact_phone', ''),
        })
    
    return data

def validate_student_data(data):
    """Validate student data before import"""
    errors = []
    
    # Check for duplicate admission numbers
    admission_numbers = [s['admission_number'] for s in data]
    duplicates = set([x for x in admission_numbers if admission_numbers.count(x) > 1])
    if duplicates:
        errors.append(f"Duplicate admission numbers: {', '.join(duplicates)}")
    
    # Check for existing students in database
    existing_admissions = Student.objects.filter(
        admission_number__in=admission_numbers
    ).values_list('admission_number', flat=True)
    if existing_admissions:
        errors.append(f"Admission numbers already exist: {', '.join(existing_admissions)}")
    
    # Check for valid class levels
    for student in data:
        if student['current_class'] not in [1, 2, 3, 4]:
            errors.append(f"Invalid class for {student['admission_number']}: {student['current_class']}")
        
        if student['gender'] not in ['M', 'F']:
            errors.append(f"Invalid gender for {student['admission_number']}: {student['gender']}")
    
    return errors

def export_student_data(students):
    """Export student data to CSV format"""
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write headers
    writer.writerow([
        'Admission Number', 'Full Name', 'Gender', 'Class', 'Stream',
        'Parent Name', 'Parent Phone', 'Boarding Status', 'Status'
    ])
    
    # Write data
    for student in students:
        writer.writerow([
            student.admission_number,
            student.get_full_name(),
            student.get_gender_display(),
            student.get_current_class_display(),
            student.get_stream_display(),
            student.parent_name,
            student.parent_phone,
            student.get_boarding_status_display(),
            'Active' if student.is_active else 'Inactive'
        ])
    
    return output.getvalue()

def calculate_student_age(dob):
    """Calculate student age from date of birth"""
    today = datetime.date.today()
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))

def get_student_performance_trend(student):
    """Get performance trend over terms"""
    from academics.models import Result
    
    results = Result.objects.filter(student=student).select_related('term')
    trend = []
    
    for result in results:
        trend.append({
            'term': str(result.term),
            'subject': result.subject.name,
            'marks': result.marks,
            'grade': result.get_grade_display(),
        })
    
    return trend

def get_class_capacity(class_level, stream):
    """Check if class has capacity for new students"""
    current_count = Student.objects.filter(
        current_class=class_level,
        stream=stream,
        is_active=True
    ).count()
    
    # Assuming maximum capacity of 45 students per stream
    capacity = 45
    available = capacity - current_count
    
    return {
        'current': current_count,
        'capacity': capacity,
        'available': available,
        'is_full': available <= 0
    }