from django.contrib import admin
from django.utils.html import format_html
from .models import (
    AcademicYear, Term, SubjectCategory, Subject, Class,
    SubjectAllocation, Exam, ExamSchedule, Result, ResultSummary,
    Timetable, LessonPlan, Homework, HomeworkSubmission
)

class TermInline(admin.TabularInline):
    model = Term
    extra = 1

@admin.register(AcademicYear)
class AcademicYearAdmin(admin.ModelAdmin):
    list_display = ['name', 'start_date', 'end_date', 'is_current']
    list_filter = ['is_current']
    search_fields = ['name']
    inlines = [TermInline]

@admin.register(Term)
class TermAdmin(admin.ModelAdmin):
    list_display = ['name', 'academic_year', 'term', 'start_date', 'end_date', 'is_current']
    list_filter = ['academic_year', 'term', 'is_current']
    search_fields = ['name']

@admin.register(SubjectCategory)
class SubjectCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'code']
    search_fields = ['name', 'code']

@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'category', 'subject_type', 'is_active']
    list_filter = ['category', 'subject_type', 'is_active']
    search_fields = ['name', 'code']

@admin.register(Class)
class ClassAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'academic_year', 'class_teacher', 'get_student_count', 'capacity']
    list_filter = ['academic_year', 'class_level', 'stream']
    search_fields = ['class_level', 'stream']
    raw_id_fields = ['class_teacher']
    
    def get_student_count(self, obj):
        return obj.get_student_count()
    get_student_count.short_description = 'Students'

@admin.register(SubjectAllocation)
class SubjectAllocationAdmin(admin.ModelAdmin):
    list_display = ['class_assigned', 'subject', 'teacher', 'lessons_per_week']
    list_filter = ['class_assigned__academic_year', 'class_assigned__class_level']
    search_fields = ['class_assigned__class_level', 'subject__name']
    raw_id_fields = ['teacher']

@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):
    list_display = ['name', 'term', 'exam_type', 'start_date', 'end_date', 'is_published']
    list_filter = ['term__academic_year', 'exam_type', 'is_published']
    search_fields = ['name']
    filter_horizontal = ['subjects']
    raw_id_fields = ['created_by']

@admin.register(ExamSchedule)
class ExamScheduleAdmin(admin.ModelAdmin):
    list_display = ['exam', 'subject', 'class_assigned', 'date', 'start_time']
    list_filter = ['exam__term', 'date']
    search_fields = ['exam__name', 'subject__name']

@admin.register(Result)
class ResultAdmin(admin.ModelAdmin):
    list_display = ['student', 'exam', 'subject', 'marks', 'grade', 'points', 'entered_by']
    list_filter = ['exam__term', 'subject']
    search_fields = ['student__admission_number', 'student__user__first_name']
    raw_id_fields = ['student', 'entered_by']
    readonly_fields = ['grade', 'points', 'entered_at', 'updated_at']

@admin.register(ResultSummary)
class ResultSummaryAdmin(admin.ModelAdmin):
    list_display = ['student', 'term', 'average', 'mean_grade', 'position_in_class']
    list_filter = ['term']
    search_fields = ['student__admission_number', 'student__user__first_name']
    raw_id_fields = ['student']

@admin.register(Timetable)
class TimetableAdmin(admin.ModelAdmin):
    list_display = ['class_assigned', 'get_day_display', 'start_time', 'end_time', 'subject', 'teacher']
    list_filter = ['class_assigned__academic_year', 'day']
    search_fields = ['class_assigned__class_level']

@admin.register(LessonPlan)
class LessonPlanAdmin(admin.ModelAdmin):
    list_display = ['teacher', 'subject', 'class_assigned', 'topic', 'week', 'lesson_number']
    list_filter = ['term', 'subject']
    search_fields = ['topic']
    raw_id_fields = ['teacher']

@admin.register(Homework)
class HomeworkAdmin(admin.ModelAdmin):
    list_display = ['title', 'subject', 'class_assigned', 'teacher', 'date_assigned', 'due_date']
    list_filter = ['subject', 'date_assigned']
    search_fields = ['title', 'description']
    raw_id_fields = ['teacher']

@admin.register(HomeworkSubmission)
class HomeworkSubmissionAdmin(admin.ModelAdmin):
    list_display = ['homework', 'student', 'submission_date', 'marks', 'graded_by']
    list_filter = ['homework__subject', 'submission_date']
    search_fields = ['student__user__first_name']
    raw_id_fields = ['student', 'graded_by']