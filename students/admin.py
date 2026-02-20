from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import (
    Student, Parent, StudentDocument, Club, Sport,
    ClubMembership, SportParticipation, StudentNote, Sibling
)

class ClubMembershipInline(admin.TabularInline):
    model = ClubMembership
    extra = 1
    raw_id_fields = ['student']

class SportParticipationInline(admin.TabularInline):
    model = SportParticipation
    extra = 1
    raw_id_fields = ['student']

class StudentDocumentInline(admin.TabularInline):
    model = StudentDocument
    extra = 1

class StudentNoteInline(admin.TabularInline):
    model = StudentNote
    extra = 1

class SiblingInline(admin.TabularInline):
    model = Sibling
    fk_name = 'student'
    extra = 1
    raw_id_fields = ['sibling']

@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = [
        'admission_number', 'full_name', 'current_class', 'stream',
        'gender', 'is_active', 'parent_phone', 'view_link'
    ]
    list_filter = ['current_class', 'stream', 'gender', 'is_active', 'boarding_status']
    search_fields = [
        'admission_number', 'kcpe_index', 'user__first_name', 'user__last_name',
        'parent_name', 'parent_phone'
    ]
    raw_id_fields = ['user', 'created_by']
    readonly_fields = ['created_at', 'updated_at']
    inlines = [
        StudentDocumentInline, StudentNoteInline, 
        ClubMembershipInline, SportParticipationInline,
        SiblingInline
    ]
    
    fieldsets = (
        ('User Account', {
            'fields': ('user',)
        }),
        ('Personal Information', {
            'fields': (
                'admission_number', 'kcpe_index', 'kcpe_marks',
                'date_of_birth', 'gender'
            )
        }),
        ('Academic Information', {
            'fields': (
                'current_class', 'stream', 'admission_class',
                'year_of_admission', 'is_active'
            )
        }),
        ('Contact Information', {
            'fields': (
                'phone_number', 'alternative_phone',  # Removed 'email'
                'physical_address', 'postal_address'
            )
        }),
        ('Parent/Guardian Information', {
            'fields': (
                'parent_name', 'parent_phone', 'parent_email',
                'parent_occupation'
            )
        }),
        ('Emergency Contact', {
            'fields': (
                'emergency_contact_name', 'emergency_contact_phone',
                'emergency_contact_relationship'
            )
        }),
        ('Additional Information', {
            'fields': (
                'boarding_status', 'medical_conditions',
                'previous_school', 'notes'
            )
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at')
        }),
    )
    
    def full_name(self, obj):
        return obj.get_full_name()
    full_name.short_description = 'Full Name'
    
    def view_link(self, obj):
        url = reverse('students:detail', args=[obj.id])
        return format_html('<a href="{}" target="_blank">View</a>', url)
    view_link.short_description = 'View'

@admin.register(Parent)
class ParentAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'relationship', 'phone_number', 'email', 'student_count']
    list_filter = ['relationship', 'emergency_contact']
    search_fields = ['full_name', 'phone_number', 'email']
    raw_id_fields = ['students']
    
    def student_count(self, obj):
        return obj.students.count()
    student_count.short_description = 'Number of Students'

@admin.register(StudentDocument)
class StudentDocumentAdmin(admin.ModelAdmin):
    list_display = ['student', 'document_type', 'title', 'uploaded_at', 'uploaded_by']
    list_filter = ['document_type', 'uploaded_at']
    search_fields = ['student__admission_number', 'title']
    readonly_fields = ['uploaded_at']

@admin.register(Club)
class ClubAdmin(admin.ModelAdmin):
    list_display = ['name', 'patron', 'chairperson', 'secretary', 'get_member_count', 'is_active']
    list_filter = ['is_active', 'meeting_day']
    search_fields = ['name', 'description']
    raw_id_fields = ['patron', 'chairperson', 'secretary', 'treasurer', 'members']
    
    def get_member_count(self, obj):
        return obj.get_member_count()
    get_member_count.short_description = 'Members'

@admin.register(Sport)
class SportAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'coach', 'captain', 'get_player_count', 'is_active']
    list_filter = ['category', 'is_active']
    search_fields = ['name', 'description']
    raw_id_fields = ['coach', 'captain', 'vice_captain', 'players']
    
    def get_player_count(self, obj):
        return obj.get_player_count()
    get_player_count.short_description = 'Players'

@admin.register(ClubMembership)
class ClubMembershipAdmin(admin.ModelAdmin):
    list_display = ['student', 'club', 'position', 'joined_date', 'is_active']
    list_filter = ['position', 'is_active', 'club']
    search_fields = ['student__user__first_name', 'student__admission_number']

@admin.register(SportParticipation)
class SportParticipationAdmin(admin.ModelAdmin):
    list_display = ['student', 'sport', 'position', 'joined_date', 'is_active']
    list_filter = ['position', 'is_active', 'sport']
    search_fields = ['student__user__first_name', 'student__admission_number']

@admin.register(StudentNote)
class StudentNoteAdmin(admin.ModelAdmin):
    list_display = ['student', 'note_type', 'title', 'created_by', 'created_at']
    list_filter = ['note_type', 'created_at']
    search_fields = ['student__admission_number', 'title', 'content']
    readonly_fields = ['created_at', 'updated_at']