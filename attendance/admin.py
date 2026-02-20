from django.contrib import admin
from django.utils.html import format_html
from .models import (
    Attendance, TeacherAttendance, AttendanceSession, DailyAttendanceRegister,
    Holiday, AttendanceReport, AttendanceNotification
)

class AttendanceSessionAdmin(admin.ModelAdmin):
    list_display = ['name', 'session_type', 'start_time', 'end_time', 'is_active']
    list_filter = ['session_type', 'is_active']
    search_fields = ['name']

class AttendanceAdmin(admin.ModelAdmin):
    list_display = ['student', 'date', 'session', 'status', 'class_level', 'stream', 'marked_by']
    list_filter = ['status', 'date', 'class_level', 'stream']
    search_fields = ['student__user__first_name', 'student__admission_number']
    date_hierarchy = 'date'
    raw_id_fields = ['student', 'marked_by']
    readonly_fields = ['marked_at', 'updated_at']
    
    fieldsets = (
        ('Student Information', {
            'fields': ('student', 'date', 'session')
        }),
        ('Attendance Details', {
            'fields': ('status', 'check_in_time', 'check_out_time', 'late_minutes', 'reason')
        }),
        ('Class Information', {
            'fields': ('class_level', 'stream')
        }),
        ('Metadata', {
            'fields': ('marked_by', 'marked_at', 'updated_at')
        }),
    )

class TeacherAttendanceAdmin(admin.ModelAdmin):
    list_display = ['teacher', 'date', 'status', 'check_in_time', 'check_out_time', 'late_minutes']
    list_filter = ['status', 'date']
    search_fields = ['teacher__user__first_name', 'teacher__employee_number']
    date_hierarchy = 'date'
    raw_id_fields = ['teacher', 'marked_by']

class DailyAttendanceRegisterAdmin(admin.ModelAdmin):
    list_display = ['class_assigned', 'date', 'session', 'total_students', 'present_count', 'absent_count', 'is_complete']
    list_filter = ['date', 'class_assigned__class_level', 'is_complete']
    search_fields = ['class_assigned__class_level', 'class_assigned__stream']
    date_hierarchy = 'date'

class HolidayAdmin(admin.ModelAdmin):
    list_display = ['name', 'holiday_type', 'date', 'is_recurring']
    list_filter = ['holiday_type', 'is_recurring', 'date']
    search_fields = ['name']
    date_hierarchy = 'date'

class AttendanceReportAdmin(admin.ModelAdmin):
    list_display = ['title', 'report_type', 'start_date', 'end_date', 'generated_by', 'generated_at']
    list_filter = ['report_type', 'generated_at']
    search_fields = ['title']
    date_hierarchy = 'generated_at'
    readonly_fields = ['generated_at']
    
    def download_link(self, obj):
        if obj.report_file:
            return format_html('<a href="{}" target="_blank">Download</a>', obj.report_file.url)
        return '-'
    download_link.short_description = 'Download'

class AttendanceNotificationAdmin(admin.ModelAdmin):
    list_display = ['student', 'attendance', 'notification_type', 'status', 'sent_at']
    list_filter = ['notification_type', 'status', 'created_at']
    search_fields = ['student__user__first_name']
    date_hierarchy = 'created_at'
    readonly_fields = ['created_at']

# Register models
admin.site.register(AttendanceSession, AttendanceSessionAdmin)
admin.site.register(Attendance, AttendanceAdmin)
admin.site.register(TeacherAttendance, TeacherAttendanceAdmin)
admin.site.register(DailyAttendanceRegister, DailyAttendanceRegisterAdmin)
admin.site.register(Holiday, HolidayAdmin)
admin.site.register(AttendanceReport, AttendanceReportAdmin)
admin.site.register(AttendanceNotification, AttendanceNotificationAdmin)