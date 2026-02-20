from django.contrib import admin
from django.utils import timezone
from django.utils.html import format_html
from django.urls import reverse
from .models import (
    Teacher, TeacherQualification, TeacherSubject, TeacherClass,
    TeacherLeave, TeacherAttendance, TeacherDocument, TeacherPerformance,
    TeacherSalary, TeacherTraining, TeacherAward, TeacherNote
)

class TeacherQualificationInline(admin.TabularInline):
    model = TeacherQualification
    extra = 1

class TeacherSubjectInline(admin.TabularInline):
    model = TeacherSubject
    extra = 1

class TeacherClassInline(admin.TabularInline):
    model = TeacherClass
    extra = 1

class TeacherDocumentInline(admin.TabularInline):
    model = TeacherDocument
    extra = 1

class TeacherNoteInline(admin.TabularInline):
    model = TeacherNote
    extra = 1

class TeacherTrainingInline(admin.TabularInline):
    model = TeacherTraining
    extra = 1

class TeacherAwardInline(admin.TabularInline):
    model = TeacherAward
    extra = 1

@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = [
        'employee_number', 'full_name', 'tsc_number', 'gender',
        'qualification_level', 'employment_type', 'is_active', 'view_link'
    ]
    list_filter = ['qualification_level', 'employment_type', 'gender', 'is_active']
    search_fields = [
        'employee_number', 'tsc_number', 'id_number',
        'user__first_name', 'user__last_name', 'phone_number'
    ]
    raw_id_fields = ['user', 'created_by']
    readonly_fields = ['created_at', 'updated_at']
    inlines = [
        TeacherQualificationInline, TeacherSubjectInline, TeacherClassInline,
        TeacherDocumentInline, TeacherNoteInline, TeacherTrainingInline,
        TeacherAwardInline
    ]
    
    fieldsets = (
        ('User Account', {
            'fields': ('user',)
        }),
        ('Personal Information', {
            'fields': (
                'employee_number', 'tsc_number', 'id_number',
                'date_of_birth', 'gender', 'marital_status'
            )
        }),
        ('Professional Information', {
            'fields': (
                'qualification_level', 'qualifications', 'specialization',
                'years_of_experience', 'date_employed', 'employment_type',
                'is_active'
            )
        }),
        ('Contact Information', {
            'fields': (
                'phone_number', 'alternative_phone', 'email',
                'physical_address', 'postal_address'
            )
        }),
        ('Emergency Contact', {
            'fields': (
                'emergency_contact_name', 'emergency_contact_phone',
                'emergency_contact_relationship'
            )
        }),
        ('Bank Details', {
            'fields': (
                'bank_name', 'bank_branch', 'bank_account', 'bank_code'
            )
        }),
        ('Medical Information', {
            'fields': ('blood_group', 'medical_conditions')
        }),
        ('Documents', {
            'fields': ('cv', 'contract', 'passport_photo')
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at')
        }),
    )
    
    def full_name(self, obj):
        return obj.get_full_name()
    full_name.short_description = 'Full Name'
    
    def view_link(self, obj):
        url = reverse('teachers:detail', args=[obj.id])
        return format_html('<a href="{}" target="_blank">View</a>', url)
    view_link.short_description = 'View'

@admin.register(TeacherLeave)
class TeacherLeaveAdmin(admin.ModelAdmin):
    list_display = ['teacher', 'leave_type', 'start_date', 'end_date', 'days_requested', 'status']
    list_filter = ['leave_type', 'status', 'start_date']
    search_fields = ['teacher__user__first_name', 'teacher__user__last_name']
    readonly_fields = ['created_at', 'updated_at']
    
    actions = ['approve_leaves', 'reject_leaves']
    
    def approve_leaves(self, request, queryset):
        queryset.update(status='approved', approved_by=request.user, approved_date=timezone.now())
    approve_leaves.short_description = "Approve selected leaves"
    
    def reject_leaves(self, request, queryset):
        queryset.update(status='rejected', approved_by=request.user, approved_date=timezone.now())
    reject_leaves.short_description = "Reject selected leaves"

@admin.register(TeacherAttendance)
class TeacherAttendanceAdmin(admin.ModelAdmin):
    list_display = ['teacher', 'date', 'status', 'check_in_time', 'check_out_time', 'late_minutes']
    list_filter = ['status', 'date']
    search_fields = ['teacher__user__first_name', 'teacher__user__last_name']
    date_hierarchy = 'date'

@admin.register(TeacherPerformance)
class TeacherPerformanceAdmin(admin.ModelAdmin):
    list_display = ['teacher', 'term', 'get_average', 'evaluation_date']
    list_filter = ['term', 'evaluation_date']
    search_fields = ['teacher__user__first_name', 'teacher__user__last_name']
    
    def get_average(self, obj):
        avg = obj.get_average_rating()
        return f"{avg:.1f}/5"
    get_average.short_description = 'Average Rating'

@admin.register(TeacherSalary)
class TeacherSalaryAdmin(admin.ModelAdmin):
    list_display = ['teacher', 'month', 'year', 'basic_salary', 'net_salary', 'payment_date']
    list_filter = ['month', 'year', 'payment_method']
    search_fields = ['teacher__user__first_name', 'teacher__user__last_name']
    
    def get_readonly_fields(self, request, obj=None):
        if obj:  # editing
            return ['net_salary']
        return []

@admin.register(TeacherDocument)
class TeacherDocumentAdmin(admin.ModelAdmin):
    list_display = ['teacher', 'document_type', 'title', 'uploaded_at', 'expiry_date']
    list_filter = ['document_type', 'uploaded_at']
    search_fields = ['teacher__user__first_name', 'title']