from django.contrib.auth.mixins import UserPassesTestMixin, LoginRequiredMixin
from django.shortcuts import redirect
from django.contrib import messages

class RoleRequiredMixin(UserPassesTestMixin):
    """Mixin to check if user has required role"""
    allowed_roles = []
    
    def test_func(self):
        return self.request.user.role in self.allowed_roles or self.request.user.is_superuser
    
    def handle_no_permission(self):
        messages.error(self.request, "You don't have permission to access this page.")
        return redirect('dashboard:home')

class StudentRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Mixin to check if user is a student"""
    
    def test_func(self):
        return self.request.user.role == 'student'
    
    def handle_no_permission(self):
        messages.error(self.request, "This page is only accessible to students.")
        return redirect('dashboard:home')

class TeacherRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Mixin to check if user is a teacher"""
    
    def test_func(self):
        return self.request.user.role == 'teacher'
    
    def handle_no_permission(self):
        messages.error(self.request, "This page is only accessible to teachers.")
        return redirect('dashboard:home')

class AdminRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Mixin to check if user is an admin"""
    
    def test_func(self):
        return self.request.user.role == 'admin' or self.request.user.is_superuser
    
    def handle_no_permission(self):
        messages.error(self.request, "This page is only accessible to administrators.")
        return redirect('dashboard:home')

class ForcePasswordChangeMixin(LoginRequiredMixin):
    """Mixin to force password change if required"""
    
    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and request.user.force_password_change:
            if request.path not in ['/accounts/change-password/', '/accounts/logout/']:
                messages.warning(request, 'Please change your password before continuing.')
                return redirect('accounts:change_password')
        return super().dispatch(request, *args, **kwargs)

class AuditLogMixin:
    """Mixin to log actions for auditing"""
    
    def log_action(self, action, model_name, object_id, object_repr, changes=None):
        from .models import AuditLog
        
        AuditLog.objects.create(
            user=self.request.user,
            action=action,
            model_name=model_name,
            object_id=object_id,
            object_repr=object_repr,
            changes=changes or {},
            ip_address=self.request.META.get('REMOTE_ADDR')
        )