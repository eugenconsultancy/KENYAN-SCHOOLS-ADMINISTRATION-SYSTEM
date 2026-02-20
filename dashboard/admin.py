from django.contrib import admin
from django.utils.html import format_html
from .models import DashboardWidget, UserDashboard, SystemHealth, ActivityLog

@admin.register(DashboardWidget)
class DashboardWidgetAdmin(admin.ModelAdmin):
    list_display = ['name', 'widget_type', 'size', 'user_role', 'is_enabled', 'order']
    list_filter = ['widget_type', 'size', 'user_role', 'is_enabled']
    search_fields = ['name', 'description']
    ordering = ['user_role', 'order']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'widget_type', 'description')
        }),
        ('Configuration', {
            'fields': ('size', 'user_role', 'data_source', 'chart_config')
        }),
        ('Display Settings', {
            'fields': ('order', 'is_enabled', 'refresh_interval')
        }),
    )
    
    readonly_fields = []

@admin.register(UserDashboard)
class UserDashboardAdmin(admin.ModelAdmin):
    list_display = ['user', 'layout', 'is_default', 'created_at']
    list_filter = ['layout', 'is_default']
    search_fields = ['user__username', 'user__email']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('User Information', {
            'fields': ('user', 'is_default')
        }),
        ('Layout Configuration', {
            'fields': ('layout', 'widget_positions')
        }),
        ('Preferences', {
            'fields': ('theme', 'color_scheme', 'compact_mode')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    filter_horizontal = []

@admin.register(SystemHealth)
class SystemHealthAdmin(admin.ModelAdmin):
    list_display = ['metric_name', 'metric_value', 'status_indicator', 'last_updated']
    list_filter = ['status', 'last_updated']
    search_fields = ['metric_name']
    readonly_fields = []
    
    def status_indicator(self, obj):
        colors = {
            'healthy': 'green',
            'warning': 'orange',
            'critical': 'red',
            'unknown': 'gray'
        }
        return format_html(
            '<span style="color: {}; font-weight: bold;">●</span> {}',
            colors.get(obj.status, 'gray'),
            obj.get_status_display()
        )
    status_indicator.short_description = 'Status'

@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ['user', 'action', 'app_name', 'ip_address', 'timestamp']
    list_filter = ['action', 'app_name', 'timestamp']
    search_fields = ['user__username', 'description', 'ip_address']
    date_hierarchy = 'timestamp'
    readonly_fields = ['timestamp']
    
    fieldsets = (
        ('Activity Information', {
            'fields': ('user', 'action', 'app_name', 'model_name', 'object_id')
        }),
        ('Details', {
            'fields': ('description', 'data', 'ip_address', 'user_agent')
        }),
        ('Timestamp', {
            'fields': ('timestamp',),
            'classes': ('collapse',)
        }),
    )
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
