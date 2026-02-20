from django.contrib.auth.models import BaseUserManager
from .models import models
class CustomUserManager(BaseUserManager):
    """Custom manager for User model with additional query methods"""
    
    def get_admins(self):
        """Return all admin users"""
        return self.filter(role='admin')
    
    def get_teachers(self):
        """Return all teachers"""
        return self.filter(role='teacher')
    
    def get_students(self):
        """Return all students"""
        return self.filter(role='student')
    
    def get_active_users(self):
        """Return all active users"""
        return self.filter(is_active=True)
    
    def get_inactive_users(self):
        """Return all inactive users"""
        return self.filter(is_active=False)
    
    def search(self, query):
        """Search users by username, email, or full name"""
        return self.filter(
            models.Q(username__icontains=query) |
            models.Q(email__icontains=query) |
            models.Q(first_name__icontains=query) |
            models.Q(last_name__icontains=query)
        )