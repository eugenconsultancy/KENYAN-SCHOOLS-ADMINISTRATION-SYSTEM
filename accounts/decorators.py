from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from django.core.exceptions import PermissionDenied

def role_required(allowed_roles=[]):
    """Decorator to check if user has required role"""
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                messages.error(request, 'Please login to access this page.')
                return redirect('accounts:login')
            
            if request.user.role in allowed_roles or request.user.is_superuser:
                return view_func(request, *args, **kwargs)
            
            # Redirect with message instead of raising PermissionDenied
            messages.error(request, "You don't have permission to access this page.")
            return redirect('dashboard:home')
        return _wrapped_view
    return decorator

def student_required(view_func):
    """Decorator to check if user is a student"""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, 'Please login to access this page.')
            return redirect('accounts:login')
        
        if request.user.role == 'student':
            return view_func(request, *args, **kwargs)
        
        messages.error(request, "This page is only accessible to students.")
        return redirect('dashboard:home')
    return _wrapped_view

def teacher_required(view_func):
    """Decorator to check if user is a teacher"""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, 'Please login to access this page.')
            return redirect('accounts:login')
        
        if request.user.role == 'teacher':
            return view_func(request, *args, **kwargs)
        
        messages.error(request, "This page is only accessible to teachers.")
        return redirect('dashboard:home')
    return _wrapped_view

def admin_required(view_func):
    """Decorator to check if user is an admin"""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, 'Please login to access this page.')
            return redirect('accounts:login')
        
        if request.user.role == 'admin' or request.user.is_superuser:
            return view_func(request, *args, **kwargs)
        
        messages.error(request, "This page is only accessible to administrators.")
        return redirect('dashboard:home')
    return _wrapped_view

def force_password_change_required(view_func):
    """Decorator to force password change if required"""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if request.user.is_authenticated and request.user.force_password_change:
            if request.path not in ['/accounts/change-password/', '/accounts/logout/']:
                messages.warning(request, 'Please change your password before continuing.')
                return redirect('accounts:change_password')
        return view_func(request, *args, **kwargs)
    return _wrapped_view