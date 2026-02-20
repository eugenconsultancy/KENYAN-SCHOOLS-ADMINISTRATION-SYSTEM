from .models import Notification
from django.utils import timezone


def site_settings(request):
    """Context processor for site-wide settings"""
    return {
        'site_name': 'Kenyan Schools System',
        'current_year': timezone.now().year,
        'current_term': 'Term 1',  # This should be dynamic
        'academic_year': '2024',
    }

def notification_count(request):
    """Context processor for unread notification count"""
    if request.user.is_authenticated:
        count = Notification.objects.filter(recipient=request.user, is_read=False).count()
        return {'unread_notifications_count': count}
    return {'unread_notifications_count': 0}

def user_role(request):
    """Context processor for user role"""
    if request.user.is_authenticated:
        return {'user_role': request.user.role}
    return {'user_role': None}