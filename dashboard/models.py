from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from accounts.models import User
import json

User = get_user_model()

class DashboardWidget(models.Model):
    """Configurable dashboard widgets"""
    
    WIDGET_TYPES = [
        ('stat', 'Statistics Card'),
        ('chart', 'Chart'),
        ('table', 'Data Table'),
        ('list', 'List'),
        ('calendar', 'Calendar'),
        ('notification', 'Notifications'),
        ('custom', 'Custom HTML'),
    ]
    
    WIDGET_SIZES = [
        ('small', 'Small (1/4 width)'),
        ('medium', 'Medium (1/2 width)'),
        ('large', 'Large (3/4 width)'),
        ('full', 'Full Width'),
    ]
    
    USER_ROLES = [
        ('admin', 'Administrator'),
        ('teacher', 'Teacher'),
        ('student', 'Student'),
        ('parent', 'Parent'),
        ('accountant', 'Accountant'),
    ]
    
    name = models.CharField(max_length=100)
    widget_type = models.CharField(max_length=20, choices=WIDGET_TYPES)
    description = models.TextField(blank=True)
    
    # Display settings
    size = models.CharField(max_length=20, choices=WIDGET_SIZES, default='medium')
    user_role = models.CharField(max_length=20, choices=USER_ROLES, default='admin')
    order = models.IntegerField(default=0)
    is_enabled = models.BooleanField(default=True)
    
    # Widget configuration
    data_source = models.CharField(max_length=200, blank=True, help_text="URL or model method to fetch data")
    chart_config = models.JSONField(default=dict, blank=True, help_text="Chart.js configuration")
    refresh_interval = models.IntegerField(default=0, help_text="Refresh interval in seconds (0 for no refresh)")
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['user_role', 'order', 'name']
    
    def __str__(self):
        return f"{self.name} ({self.get_user_role_display()})"
    
    def get_widget_data(self, user=None):
        """Fetch data for this widget"""
        if not self.data_source:
            return None
        
        try:
            # Parse data source (format: app.model.method or url)
            if '.' in self.data_source:
                # Model method reference
                parts = self.data_source.split('.')
                if len(parts) == 3:
                    app, model, method = parts
                    # Dynamically import and call method
                    module = __import__(f'{app}.models', fromlist=[model])
                    model_class = getattr(module, model)
                    if user:
                        result = getattr(model_class, method)(user)
                    else:
                        result = getattr(model_class, method)()
                    return result
            return None
        except Exception as e:
            return {'error': str(e)}

class UserDashboard(models.Model):
    """User-specific dashboard configuration"""
    
    LAYOUT_CHOICES = [
        ('grid', 'Grid Layout'),
        ('masonry', 'Masonry Layout'),
        ('columns', 'Columns Layout'),
    ]
    
    THEME_CHOICES = [
        ('light', 'Light Theme'),
        ('dark', 'Dark Theme'),
        ('auto', 'Auto (System Default)'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='dashboard_config')
    
    # Layout settings
    layout = models.CharField(max_length=20, choices=LAYOUT_CHOICES, default='grid')
    widgets = models.ManyToManyField(DashboardWidget, through='DashboardWidgetPosition')
    
    # Widget positions (stored as JSON)
    widget_positions = models.JSONField(default=dict, blank=True)
    
    # Preferences
    theme = models.CharField(max_length=20, choices=THEME_CHOICES, default='light')
    color_scheme = models.CharField(max_length=50, default='blue')
    compact_mode = models.BooleanField(default=False)
    
    # Default dashboard
    is_default = models.BooleanField(default=False)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-is_default', 'user__username']
    
    def __str__(self):
        return f"{self.user.username}'s Dashboard"
    
    def get_widgets_ordered(self):
        """Get widgets in their proper order"""
        return self.widgets.order_by('dashboardwidgetposition__position')

class DashboardWidgetPosition(models.Model):
    """Through model for widget positioning"""
    
    dashboard = models.ForeignKey(UserDashboard, on_delete=models.CASCADE)
    widget = models.ForeignKey(DashboardWidget, on_delete=models.CASCADE)
    position = models.IntegerField(default=0)
    column = models.IntegerField(default=0)
    row = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['row', 'column', 'position']
        unique_together = ['dashboard', 'widget']
    
    def __str__(self):
        return f"{self.widget.name} at ({self.row}, {self.column})"

class SystemHealth(models.Model):
    """System health monitoring"""
    
    STATUS_CHOICES = [
        ('healthy', 'Healthy'),
        ('warning', 'Warning'),
        ('critical', 'Critical'),
        ('unknown', 'Unknown'),
    ]
    
    metric_name = models.CharField(max_length=100, unique=True)
    metric_value = models.CharField(max_length=255)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='healthy')
    message = models.TextField(blank=True)
    last_updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name_plural = "System Health"
        ordering = ['metric_name']
    
    def __str__(self):
        return f"{self.metric_name}: {self.metric_value} ({self.get_status_display()})"

class ActivityLog(models.Model):
    """User activity logging"""
    
    ACTION_CHOICES = [
        ('login', 'Login'),
        ('logout', 'Logout'),
        ('view', 'View'),
        ('create', 'Create'),
        ('update', 'Update'),
        ('delete', 'Delete'),
        ('export', 'Export'),
        ('import', 'Import'),
        ('print', 'Print'),
        ('download', 'Download'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    app_name = models.CharField(max_length=50)
    model_name = models.CharField(max_length=50, blank=True)
    object_id = models.CharField(max_length=50, blank=True)
    
    description = models.TextField()
    data = models.JSONField(default=dict, blank=True)
    
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', '-timestamp']),
            models.Index(fields=['app_name', '-timestamp']),
            models.Index(fields=['action', '-timestamp']),
        ]
    
    def __str__(self):
        return f"{self.user} - {self.action} - {self.timestamp}"
    
    @classmethod
    def log_activity(cls, user, action, app_name, description, **kwargs):
        """Create an activity log entry"""
        return cls.objects.create(
            user=user,
            action=action,
            app_name=app_name,
            description=description,
            **kwargs
        )