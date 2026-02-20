from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q
from django.core.paginator import Paginator
from django.http import JsonResponse
from .decorators import role_required
from .models import User, LoginLog, AuditLog, Notification
from .forms import (
    CustomUserCreationForm, CustomUserChangeForm, 
    CustomAuthenticationForm, ProfileUpdateForm,
    PasswordChangeForm, NotificationForm
)
import json

def login_view(request):
    """Handle user login"""
    if request.user.is_authenticated:
        return redirect('dashboard:home')
    
    if request.method == 'POST':
        form = CustomAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            # Get the cleaned data
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            
            # Authenticate the user
            user = authenticate(request, username=username, password=password)
            
            # If authentication fails, try with email
            if user is None:
                try:
                    user_obj = User.objects.get(email=username)
                    user = authenticate(request, username=user_obj.username, password=password)
                except User.DoesNotExist:
                    pass
            
            if user is not None:
                # Check if user is active
                if not user.is_active:
                    messages.error(request, 'This account is deactivated. Contact administrator.')
                    return render(request, 'accounts/login.html', {'form': form})
                
                # Log the user in
                login(request, user)
                
                # Log the login
                LoginLog.objects.create(
                    user=user,
                    ip_address=request.META.get('REMOTE_ADDR'),
                    user_agent=request.META.get('HTTP_USER_AGENT', ''),
                    success=True
                )
                
                # Create audit log
                AuditLog.objects.create(
                    user=user,
                    action='LOGIN',
                    model_name='User',
                    object_id=user.id,
                    object_repr=str(user),
                    ip_address=request.META.get('REMOTE_ADDR')
                )
                
                # Update last login IP
                user.last_login_ip = request.META.get('REMOTE_ADDR')
                user.save(update_fields=['last_login_ip'])
                
                # Check if password change is required
                if user.force_password_change:
                    messages.warning(request, 'Please change your password before continuing.')
                    return redirect('accounts:change_password')
                
                # Redirect based on role
                if user.role == 'admin':
                    return redirect('admin:index')
                elif user.role == 'teacher':
                    return redirect('teachers:dashboard')
                elif user.role == 'student':
                    return redirect('students:dashboard')
                elif user.role == 'parent':
                    return redirect('dashboard:parent')
                elif user.role == 'accountant':
                    return redirect('dashboard:accountant')
                else:
                    return redirect('dashboard:home')
            else:
                messages.error(request, 'Invalid username or password.')
        else:
            messages.error(request, 'Invalid username or password.')
    else:
        form = CustomAuthenticationForm()
    
    return render(request, 'accounts/login.html', {'form': form})

@login_required
def logout_view(request):
    """Handle user logout"""
    # Log the logout
    LoginLog.objects.create(
        user=request.user,
        ip_address=request.META.get('REMOTE_ADDR'),
        user_agent=request.META.get('HTTP_USER_AGENT', ''),
        success=True
    )
    
    # Create audit log
    AuditLog.objects.create(
        user=request.user,
        action='LOGOUT',
        model_name='User',
        object_id=request.user.id,
        object_repr=str(request.user),
        ip_address=request.META.get('REMOTE_ADDR')
    )
    
    logout(request)
    messages.success(request, 'You have been successfully logged out.')
    return redirect('accounts:login')

@login_required
def profile_view(request):
    """View user profile"""
    return render(request, 'accounts/profile.html', {'user': request.user})

@login_required
def profile_edit(request):
    """Edit user profile"""
    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            
            # Create audit log
            AuditLog.objects.create(
                user=request.user,
                action='UPDATE',
                model_name='User',
                object_id=request.user.id,
                object_repr=str(request.user),
                changes={'profile_updated': True},
                ip_address=request.META.get('REMOTE_ADDR')
            )
            
            messages.success(request, 'Profile updated successfully.')
            return redirect('accounts:profile')
    else:
        form = ProfileUpdateForm(instance=request.user)
    
    return render(request, 'accounts/profile_edit.html', {'form': form})

@login_required
def change_password(request):
    """Change user password"""
    if request.method == 'POST':
        form = PasswordChangeForm(request.POST)
        if form.is_valid():
            user = request.user
            if user.check_password(form.cleaned_data['old_password']):
                user.set_password(form.cleaned_data['new_password1'])
                user.force_password_change = False
                user.save()
                
                # Update session to prevent logout
                update_session_auth_hash(request, user)
                
                # Create audit log
                AuditLog.objects.create(
                    user=user,
                    action='UPDATE',
                    model_name='User',
                    object_id=user.id,
                    object_repr=str(user),
                    changes={'password_changed': True},
                    ip_address=request.META.get('REMOTE_ADDR')
                )
                
                messages.success(request, 'Password changed successfully.')
                return redirect('accounts:profile')
            else:
                messages.error(request, 'Current password is incorrect.')
    else:
        form = PasswordChangeForm()
    
    return render(request, 'accounts/change_password.html', {'form': form})

@login_required
@role_required(['admin'])
def user_list(request):
    """List all users (admin only)"""
    users = User.objects.all().order_by('-date_joined')
    
    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        users = users.filter(
            Q(username__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query)
        )
    
    # Filter by role
    role_filter = request.GET.get('role', '')
    if role_filter:
        users = users.filter(role=role_filter)
    
    # Get user roles for filter dropdown
    user_roles = User.ROLE_CHOICES
    
    # Pagination
    paginator = Paginator(users, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'accounts/user_list.html', {
        'page_obj': page_obj,
        'search_query': search_query,
        'role_filter': role_filter,
        'user_roles': user_roles,
    })

@login_required
@role_required(['admin'])
def user_create(request):
    """Create new user (admin only)"""
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save()
            
            # Create audit log
            AuditLog.objects.create(
                user=request.user,
                action='CREATE',
                model_name='User',
                object_id=user.id,
                object_repr=str(user),
                ip_address=request.META.get('REMOTE_ADDR')
            )
            
            messages.success(request, f'User {user.username} created successfully.')
            return redirect('accounts:user_list')
    else:
        form = CustomUserCreationForm()
    
    return render(request, 'accounts/user_form.html', {'form': form, 'title': 'Create User'})

@login_required
@role_required(['admin'])
def user_edit(request, user_id):
    """Edit user (admin only)"""
    user = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        form = CustomUserChangeForm(request.POST, request.FILES, instance=user)
        if form.is_valid():
            form.save()
            
            # Create audit log
            AuditLog.objects.create(
                user=request.user,
                action='UPDATE',
                model_name='User',
                object_id=user.id,
                object_repr=str(user),
                ip_address=request.META.get('REMOTE_ADDR')
            )
            
            messages.success(request, f'User {user.username} updated successfully.')
            return redirect('accounts:user_list')
    else:
        form = CustomUserChangeForm(instance=user)
    
    return render(request, 'accounts/user_form.html', {'form': form, 'title': 'Edit User'})

@login_required
@role_required(['admin'])
def user_delete(request, user_id):
    """Delete user (admin only)"""
    user = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        username = user.username
        user.delete()
        
        # Create audit log
        AuditLog.objects.create(
            user=request.user,
            action='DELETE',
            model_name='User',
            object_id=user_id,
            object_repr=username,
            ip_address=request.META.get('REMOTE_ADDR')
        )
        
        messages.success(request, f'User {username} deleted successfully.')
        return redirect('accounts:user_list')
    
    return render(request, 'accounts/user_confirm_delete.html', {'user': user})

@login_required
def notifications(request):
    """View user notifications"""
    notifications_list = Notification.objects.filter(recipient=request.user).order_by('-created_at')
    
    # Mark all as read
    if request.GET.get('mark_read'):
        notifications_list.update(is_read=True, read_at=timezone.now())
        messages.success(request, 'All notifications marked as read.')
        return redirect('accounts:notifications')
    
    # Pagination
    paginator = Paginator(notifications_list, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'accounts/notifications.html', {'page_obj': page_obj})

@login_required
def notification_detail(request, notification_id):
    """View single notification"""
    notification = get_object_or_404(Notification, id=notification_id, recipient=request.user)
    
    if not notification.is_read:
        notification.mark_as_read()
    
    return render(request, 'accounts/notification_detail.html', {'notification': notification})

@login_required
def notification_mark_read(request, notification_id):
    """Mark notification as read (AJAX)"""
    if request.method == 'POST' and request.headers.get('x-requested-with') == 'XMLHttpRequest':
        notification = get_object_or_404(Notification, id=notification_id, recipient=request.user)
        notification.mark_as_read()
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error'}, status=400)

@login_required
def activity_log(request):
    """View user activity log"""
    logs = AuditLog.objects.filter(user=request.user).order_by('-timestamp')
    
    # Pagination
    paginator = Paginator(logs, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'accounts/activity_log.html', {'page_obj': page_obj})

@login_required
@role_required(['admin'])
def audit_logs(request):
    """View all audit logs (admin only)"""
    logs = AuditLog.objects.all().order_by('-timestamp')
    
    # Filter by user
    user_filter = request.GET.get('user', '')
    if user_filter:
        logs = logs.filter(user_id=user_filter)
    
    # Filter by action
    action_filter = request.GET.get('action', '')
    if action_filter:
        logs = logs.filter(action=action_filter)
    
    # Pagination
    paginator = Paginator(logs, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'user_filter': user_filter,
        'action_filter': action_filter,
        'users': User.objects.all(),
        'actions': AuditLog.ACTION_TYPES,
    }
    
    return render(request, 'accounts/audit_logs.html', context)