from django.core.management.base import BaseCommand
from django.utils import timezone
from accounts.models import User
from students.models import Student
from teachers.models import Teacher
from academics.models import (
    AcademicYear, Term, SubjectCategory, Subject, Class, 
    SubjectAllocation, Exam, Result
)
from finance.models import FeeStructure, Invoice, Payment
from attendance.models import Attendance, AttendanceSession
import datetime
import random

class Command(BaseCommand):
    help = 'Populates the database with sample data in correct order'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS('Starting data population...'))
        
        # Step 1: Create Academic Years and Terms
        self.create_academic_years()
        
        # Step 2: Create Subject Categories and Subjects
        self.create_subjects()
        
        # Step 3: Create Classes
        self.create_classes()
        
        # Step 4: Create Teachers
        self.create_teachers()
        
        # Step 5: Create Students
        self.create_students()
        
        # Step 6: Create Subject Allocations
        self.create_subject_allocations()
        
        # Step 7: Create Fee Structures
        self.create_fee_structures()
        
        # Step 8: Create Invoices
        self.create_invoices()
        
        # Step 9: Create Exams and Results
        self.create_exams_and_results()
        
        # Step 10: Create Attendance
        self.create_attendance()
        
        self.stdout.write(self.style.SUCCESS('✓ Data population complete!'))

    def create_academic_years(self):
        self.stdout.write('Creating Academic Years and Terms...')
        
        # Create 2024 Academic Year
        year2024, created = AcademicYear.objects.get_or_create(
            name='2024',
            defaults={
                'start_date': datetime.date(2024, 1, 15),
                'end_date': datetime.date(2024, 11, 30),
                'is_current': True
            }
        )
        
        # Create Terms for 2024
        Term.objects.get_or_create(
            academic_year=year2024,
            term=1,
            defaults={
                'name': 'Term 1 2024',
                'start_date': datetime.date(2024, 1, 15),
                'end_date': datetime.date(2024, 4, 15),
                'is_current': True
            }
        )
        Term.objects.get_or_create(
            academic_year=year2024,
            term=2,
            defaults={
                'name': 'Term 2 2024',
                'start_date': datetime.date(2024, 5, 1),
                'end_date': datetime.date(2024, 8, 15),
                'is_current': False
            }
        )
        Term.objects.get_or_create(
            academic_year=year2024,
            term=3,
            defaults={
                'name': 'Term 3 2024',
                'start_date': datetime.date(2024, 9, 1),
                'end_date': datetime.date(2024, 11, 30),
                'is_current': False
            }
        )
        
        # Create 2025 Academic Year
        year2025, created = AcademicYear.objects.get_or_create(
            name='2025',
            defaults={
                'start_date': datetime.date(2025, 1, 15),
                'end_date': datetime.date(2025, 11, 30),
                'is_current': False
            }
        )
        
        self.stdout.write(self.style.SUCCESS('  ✓ Academic Years and Terms created'))

    def create_subjects(self):
        self.stdout.write('Creating Subject Categories and Subjects...')
        
        # Create Categories
        sciences, _ = SubjectCategory.objects.get_or_create(
            name='Sciences',
            code='SCI'
        )
        humanities, _ = SubjectCategory.objects.get_or_create(
            name='Humanities',
            code='HUM'
        )
        languages, _ = SubjectCategory.objects.get_or_create(
            name='Languages',
            code='LAN'
        )
        mathematics, _ = SubjectCategory.objects.get_or_create(
            name='Mathematics',
            code='MATH'
        )
        technical, _ = SubjectCategory.objects.get_or_create(
            name='Technical',
            code='TECH'
        )
        
        # Create Subjects
        subjects_data = [
            {'name': 'Mathematics', 'code': 'MAT', 'category': mathematics, 'classes': [1,2,3,4]},
            {'name': 'English', 'code': 'ENG', 'category': languages, 'classes': [1,2,3,4]},
            {'name': 'Kiswahili', 'code': 'KIS', 'category': languages, 'classes': [1,2,3,4]},
            {'name': 'Biology', 'code': 'BIO', 'category': sciences, 'classes': [1,2,3,4]},
            {'name': 'Chemistry', 'code': 'CHE', 'category': sciences, 'classes': [2,3,4]},
            {'name': 'Physics', 'code': 'PHY', 'category': sciences, 'classes': [2,3,4]},
            {'name': 'History', 'code': 'HIS', 'category': humanities, 'classes': [1,2,3,4]},
            {'name': 'Geography', 'code': 'GEO', 'category': humanities, 'classes': [1,2,3,4]},
            {'name': 'CRE', 'code': 'CRE', 'category': humanities, 'classes': [1,2,3,4]},
            {'name': 'Business Studies', 'code': 'BUS', 'category': humanities, 'classes': [1,2,3,4]},
            {'name': 'Agriculture', 'code': 'AGR', 'category': sciences, 'classes': [1,2,3,4]},
            {'name': 'Computer Studies', 'code': 'COM', 'category': technical, 'classes': [1,2,3,4]},
        ]
        
        for data in subjects_data:
            Subject.objects.get_or_create(
                code=data['code'],
                defaults={
                    'name': data['name'],
                    'category': data['category'],
                    'classes': data['classes'],
                    'subject_type': 'compulsory',
                    'pass_mark': 40,
                    'max_mark': 100,
                    'is_active': True
                }
            )
        
        self.stdout.write(self.style.SUCCESS('  ✓ Subjects created'))

    def create_classes(self):
        self.stdout.write('Creating Classes...')
        
        academic_year = AcademicYear.objects.get(name='2024')
        
        streams = ['East', 'West', 'North', 'South']
        classes_created = 0
        
        for form in range(1, 5):
            for stream in streams:
                class_obj, created = Class.objects.get_or_create(
                    class_level=form,
                    stream=stream,
                    academic_year=academic_year,
                    defaults={
                        'capacity': 45
                    }
                )
                if created:
                    classes_created += 1
        
        self.stdout.write(self.style.SUCCESS(f'  ✓ {classes_created} Classes created'))

    def create_teachers(self):
        self.stdout.write('Creating Teachers...')
        
        teachers_data = [
            {
                'username': 'john.odhiambo',
                'email': 'john.odhiambo@school.com',
                'first_name': 'John',
                'last_name': 'Odhiambo',
                'employee_number': 'TCH001',
                'tsc_number': 'TSC001',
                'id_number': '12345678',
                'specialization': 'Mathematics',
                'phone': '0712345678'
            },
            {
                'username': 'jane.wanjiku',
                'email': 'jane.wanjiku@school.com',
                'first_name': 'Jane',
                'last_name': 'Wanjiku',
                'employee_number': 'TCH002',
                'tsc_number': 'TSC002',
                'id_number': '23456789',
                'specialization': 'English',
                'phone': '0723456789'
            },
            {
                'username': 'peter.otieno',
                'email': 'peter.otieno@school.com',
                'first_name': 'Peter',
                'last_name': 'Otieno',
                'employee_number': 'TCH003',
                'tsc_number': 'TSC003',
                'id_number': '34567890',
                'specialization': 'Chemistry',
                'phone': '0734567890'
            },
            {
                'username': 'mary.atieno',
                'email': 'mary.atieno@school.com',
                'first_name': 'Mary',
                'last_name': 'Atieno',
                'employee_number': 'TCH004',
                'tsc_number': 'TSC004',
                'id_number': '45678901',
                'specialization': 'Biology',
                'phone': '0745678901'
            },
            {
                'username': 'david.kiplagat',
                'email': 'david.kiplagat@school.com',
                'first_name': 'David',
                'last_name': 'Kiplagat',
                'employee_number': 'TCH005',
                'tsc_number': 'TSC005',
                'id_number': '56789012',
                'specialization': 'History',
                'phone': '0756789012'
            },
        ]
        
        for data in teachers_data:
            user, created = User.objects.get_or_create(
                username=data['username'],
                defaults={
                    'email': data['email'],
                    'first_name': data['first_name'],
                    'last_name': data['last_name'],
                    'role': 'teacher',
                    'phone_number': data['phone'],
                    'is_active': True
                }
            )
            if created:
                user.set_password('Teacher@2024')
                user.save()
                
                Teacher.objects.get_or_create(
                    user=user,
                    defaults={
                        'employee_number': data['employee_number'],
                        'tsc_number': data['tsc_number'],
                        'id_number': data['id_number'],
                        'date_of_birth': datetime.date(1985, random.randint(1,12), random.randint(1,28)),
                        'gender': random.choice(['M', 'F']),
                        'marital_status': random.choice(['single', 'married']),
                        'qualification_level': 'bachelors',
                        'qualifications': f'B.Ed in {data["specialization"]}',
                        'specialization': data['specialization'],
                        'years_of_experience': random.randint(5, 15),
                        'date_employed': datetime.date(2015, 1, 1),
                        'employment_type': 'permanent',
                        'phone_number': data['phone'],
                        'email': data['email'],
                        'emergency_contact_name': 'Emergency Contact',
                        'emergency_contact_phone': '0798765432',
                        'emergency_contact_relationship': 'Spouse',
                        'is_active': True
                    }
                )
        
        self.stdout.write(self.style.SUCCESS('  ✓ Teachers created'))

    def create_students(self):
        self.stdout.write('Creating Students...')
        
        first_names = ['James', 'Mary', 'John', 'Patricia', 'Robert', 'Jennifer', 'Michael', 'Linda', 'William', 'Elizabeth']
        last_names = ['Odhiambo', 'Wanjiku', 'Otieno', 'Achieng', 'Kipchoge', 'Mwangi', 'Karanja', 'Omondi', 'Kiplagat', 'Chebet']
        
        students_created = 0
        
        for form in range(1, 5):
            for stream in ['East', 'West', 'North', 'South']:
                # Create 30 students per class
                for i in range(1, 31):
                    first_name = random.choice(first_names)
                    last_name = random.choice(last_names)
                    username = f"{first_name.lower()}.{last_name.lower()}.{form}{stream[:1]}{i}"
                    
                    user, created = User.objects.get_or_create(
                        username=username,
                        defaults={
                            'email': f"{username}@student.school.com",
                            'first_name': first_name,
                            'last_name': last_name,
                            'role': 'student',
                            'phone_number': f"07{random.randint(10000000, 99999999)}",
                            'is_active': True
                        }
                    )
                    
                    if created:
                        user.set_password('Student@2024')
                        user.save()
                        
                        # Calculate KCPE marks between 250-400
                        kcpe_marks = random.randint(250, 400)
                        
                        Student.objects.get_or_create(
                            user=user,
                            defaults={
                                'admission_number': f"ADM/{2024}/{form}{stream[:1]}{i:03d}",
                                'kcpe_index': f"2023/{random.randint(100,999)}/{random.randint(1000,9999)}",
                                'kcpe_marks': kcpe_marks,
                                'date_of_birth': datetime.date(2008 - form, random.randint(1,12), random.randint(1,28)),
                                'gender': random.choice(['M', 'F']),
                                'current_class': form,
                                'stream': stream,
                                'admission_class': form,
                                'year_of_admission': 2024,
                                'parent_name': f"Parent of {first_name} {last_name}",
                                'parent_phone': f"07{random.randint(10000000, 99999999)}",
                                'emergency_contact_name': f"Emergency {first_name} {last_name}",
                                'emergency_contact_phone': f"07{random.randint(10000000, 99999999)}",
                                'emergency_contact_relationship': random.choice(['Parent', 'Guardian']),
                                'boarding_status': random.choice(['boarder', 'day_scholar']),
                                'is_active': True
                            }
                        )
                        students_created += 1
        
        self.stdout.write(self.style.SUCCESS(f'  ✓ {students_created} Students created'))

    def create_subject_allocations(self):
        self.stdout.write('Creating Subject Allocations...')
        
        academic_year = AcademicYear.objects.get(name='2024')
        teachers = list(Teacher.objects.all())
        subjects = list(Subject.objects.all())
        
        allocations_created = 0
        
        for form in range(1, 5):
            for stream in ['East', 'West', 'North', 'South']:
                try:
                    class_obj = Class.objects.get(
                        class_level=form,
                        stream=stream,
                        academic_year=academic_year
                    )
                    
                    # Allocate subjects suitable for this form
                    for subject in subjects:
                        if form in subject.classes:
                            teacher = random.choice(teachers) if teachers else None
                            
                            _, created = SubjectAllocation.objects.get_or_create(
                                class_assigned=class_obj,
                                subject=subject,
                                defaults={
                                    'teacher': teacher,
                                    'lessons_per_week': random.choice([3, 4, 5])
                                }
                            )
                            if created:
                                allocations_created += 1
                except Class.DoesNotExist:
                    continue
        
        self.stdout.write(self.style.SUCCESS(f'  ✓ {allocations_created} Subject Allocations created'))

    def create_fee_structures(self):
        self.stdout.write('Creating Fee Structures...')
        
        academic_year = AcademicYear.objects.get(name='2024')
        
        for term in [1, 2, 3]:
            for form in range(1, 5):
                # Calculate fees based on form level
                tuition = 25000 + (form * 5000)
                boarding = 15000 if form > 2 else 12000
                
                FeeStructure.objects.get_or_create(
                    academic_year=academic_year,
                    term=term,
                    class_level=form,
                    defaults={
                        'name': f'Form {form} - Term {term} 2024',
                        'tuition_fee': tuition,
                        'boarding_fee': boarding,
                        'transport_fee': 5000,
                        'library_fee': 2000,
                        'sports_fee': 1500,
                        'medical_fee': 1000,
                        'development_fee': 3000,
                        'other_fees': 1000,
                        'payment_deadline': datetime.date(2024, term*3, 15),
                        'late_payment_penalty': 1000,
                        'is_active': True
                    }
                )
        
        self.stdout.write(self.style.SUCCESS('  ✓ Fee Structures created'))

    def create_invoices(self):
        self.stdout.write('Creating Invoices...')
        
        academic_year = AcademicYear.objects.get(name='2024')
        students = Student.objects.all()
        
        invoices_created = 0
        
        for student in students:
            for term in [1, 2, 3]:
                try:
                    fee_structure = FeeStructure.objects.get(
                        academic_year=academic_year,
                        term=term,
                        class_level=student.current_class
                    )
                    
                    total = fee_structure.get_total_fee()
                    
                    invoice, created = Invoice.objects.get_or_create(
                        student=student,
                        fee_structure=fee_structure,
                        defaults={
                            'due_date': fee_structure.payment_deadline,
                            'subtotal': total,
                            'total_amount': total,
                            'balance': total,
                            'status': random.choice(['sent', 'paid', 'partially_paid']),
                            'notes': f'Fees for Term {term} 2024'
                        }
                    )
                    
                    if created:
                        invoices_created += 1
                        
                        # Create some payments for paid invoices
                        if invoice.status == 'paid':
                            Payment.objects.create(
                                student=student,
                                invoice=invoice,
                                amount=total,
                                payment_date=timezone.now() - datetime.timedelta(days=random.randint(1, 30)),
                                payment_method=random.choice(['cash', 'mpesa', 'bank_transfer']),
                                payment_status='completed',
                                reference_number=f'REF{random.randint(10000,99999)}',
                                notes='Payment completed'
                            )
                            invoice.amount_paid = total
                            invoice.balance = 0
                            invoice.save()
                        elif invoice.status == 'partially_paid':
                            paid = random.randint(1, int(total * 0.7))
                            Payment.objects.create(
                                student=student,
                                invoice=invoice,
                                amount=paid,
                                payment_date=timezone.now() - datetime.timedelta(days=random.randint(1, 15)),
                                payment_method=random.choice(['cash', 'mpesa']),
                                payment_status='completed',
                                reference_number=f'REF{random.randint(10000,99999)}',
                                notes='Partial payment'
                            )
                            invoice.amount_paid = paid
                            invoice.balance = total - paid
                            invoice.save()
                            
                except (FeeStructure.DoesNotExist, Class.DoesNotExist):
                    continue
        
        self.stdout.write(self.style.SUCCESS(f'  ✓ {invoices_created} Invoices created'))

    def create_exams_and_results(self):
        self.stdout.write('Creating Exams and Results...')
        
        academic_year = AcademicYear.objects.get(name='2024')
        term = Term.objects.get(academic_year=academic_year, term=1)
        subjects = Subject.objects.all()
        
        # Create End Term Exam
        exam, _ = Exam.objects.get_or_create(
            name='End Term 1 Examination 2024',
            term=term,
            defaults={
                'exam_type': 'endterm',
                'start_date': datetime.date(2024, 4, 1),
                'end_date': datetime.date(2024, 4, 10),
                'description': 'End of Term 1 Examinations',
                'is_published': True
            }
        )
        
        # Add subjects to exam
        exam.subjects.set(subjects)
        
        # Create results for students
        students = Student.objects.all()
        results_created = 0
        
        for student in students:
            for subject in subjects:
                if student.current_class in subject.classes:
                    marks = random.randint(30, 95)
                    Result.objects.get_or_create(
                        student=student,
                        exam=exam,
                        subject=subject,
                        defaults={
                            'marks': marks,
                            'remarks': random.choice(['Good performance', 'Needs improvement', 'Satisfactory', 'Excellent']),
                        }
                    )
                    results_created += 1
        
        self.stdout.write(self.style.SUCCESS(f'  ✓ {results_created} Results created'))

    def create_attendance(self):
        self.stdout.write('Creating Attendance Records...')
        
        # Create attendance sessions
        morning, _ = AttendanceSession.objects.get_or_create(
            name='Morning Session',
            session_type='morning',
            start_time='08:00',
            end_time='12:00'
        )
        
        afternoon, _ = AttendanceSession.objects.get_or_create(
            name='Afternoon Session',
            session_type='afternoon',
            start_time='13:00',
            end_time='16:00'
        )
        
        # Create attendance for last 30 days
        students = Student.objects.filter(is_active=True)
        end_date = timezone.now().date()
        start_date = end_date - datetime.timedelta(days=30)
        
        attendance_created = 0
        
        current_date = start_date
        while current_date <= end_date:
            # Skip Sundays
            if current_date.weekday() != 6:  # 6 is Sunday
                for student in students:
                    # 85% attendance rate
                    if random.random() < 0.85:
                        status = random.choices(
                            ['present', 'absent', 'late', 'excused'],
                            weights=[0.80, 0.10, 0.05, 0.05]
                        )[0]
                        
                        check_in = None
                        if status in ['present', 'late']:
                            check_in = datetime.time(
                                random.randint(7, 9) if status == 'late' else random.randint(7, 8),
                                random.randint(0, 59)
                            )
                        
                        Attendance.objects.get_or_create(
                            student=student,
                            date=current_date,
                            session=morning if random.random() < 0.5 else afternoon,
                            defaults={
                                'status': status,
                                'check_in_time': check_in,
                                'class_level': student.current_class,
                                'stream': student.stream,
                                'reason': 'Sick' if status == 'absent' and random.random() < 0.3 else ''
                            }
                        )
                        attendance_created += 1
            current_date += datetime.timedelta(days=1)
        
        self.stdout.write(self.style.SUCCESS(f'  ✓ {attendance_created} Attendance records created'))
