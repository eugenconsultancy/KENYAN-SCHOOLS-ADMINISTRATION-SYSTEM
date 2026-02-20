from django.utils import timezone
from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages
from .models import AuditLog

class RoleBasedAccessMiddleware:
    """Middleware to restrict access based on user roles"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Define role-based access rules
        restricted_paths = {
            '/admin/': ['admin'],
            '/students/': ['student', 'teacher', 'admin'],
            '/teachers/': ['teacher', 'admin'],
            '/finance/': ['accountant', 'admin'],
            '/reports/': ['admin', 'teacher'],
        }
        
        # Check if user is authenticated
        if request.user.is_authenticated:
            # Check each restricted path
            for path, allowed_roles in restricted_paths.items():
                if request.path.startswith(path):
                    if request.user.role not in allowed_roles and not request.user.is_superuser:
                        messages.error(request, 'You do not have permission to access this page.')
                        return redirect('dashboard:home')
        
        response = self.get_response(request)
        return response

class AuditLogMiddleware:
    """Middleware to log user actions"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        response = self.get_response(request)
        
        # Log POST requests for audit trail
        if request.method == 'POST' and request.user.is_authenticated:
            # Skip logging for certain paths
            skip_paths = ['/accounts/login/', '/accounts/logout/']
            
            if not any(request.path.startswith(path) for path in skip_paths):
                # Log the action
                AuditLog.objects.create(
                    user=request.user,
                    action='UPDATE' if 'update' in request.path else 'CREATE',
                    model_name='Unknown',
                    object_id='0',
                    object_repr='POST Request',
                    changes={'path': request.path, 'data': dict(request.POST)},
                    ip_address=request.META.get('REMOTE_ADDR')
                )
        
        return response

class LastActivityMiddleware:
    """Middleware to update user's last activity timestamp"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        response = self.get_response(request)
        
        if request.user.is_authenticated:
            # Update last activity
            request.user.last_activity = timezone.now()
            request.user.save(update_fields=['last_activity'])
        
        return response