from django.db.models.signals import post_save, pre_save, post_delete
from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver
from django.utils import timezone
from .models import User, LoginLog, AuditLog, Notification

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Create profile or perform actions when user is created"""
    if created:
        # Send welcome notification
        Notification.objects.create(
            recipient=instance,
            title='Welcome to Kenyan Schools System',
            message=f'Welcome {instance.get_full_name() or instance.username}! We\'re glad to have you on board.',
            notification_type='success'
        )
        
        # Create audit log
        AuditLog.objects.create(
            user=instance,
            action='CREATE',
            model_name='User',
            object_id=instance.id,
            object_repr=str(instance)
        )

@receiver(pre_save, sender=User)
def track_user_changes(sender, instance, **kwargs):
    """Track changes before saving user"""
    if instance.pk:
        try:
            old_instance = User.objects.get(pk=instance.pk)
            
            # Track changes
            changes = {}
            fields_to_track = ['username', 'email', 'first_name', 'last_name', 'role', 'is_active']
            
            for field in fields_to_track:
                old_value = getattr(old_instance, field)
                new_value = getattr(instance, field)
                if old_value != new_value:
                    changes[field] = {
                        'old': str(old_value),
                        'new': str(new_value)
                    }
            
            if changes:
                # Store changes in instance for post_save signal
                instance._changes = changes
        except User.DoesNotExist:
            pass

@receiver(post_save, sender=User)
def log_user_changes(sender, instance, created, **kwargs):
    """Log changes after saving user"""
    if not created and hasattr(instance, '_changes'):
        AuditLog.objects.create(
            user=instance,
            action='UPDATE',
            model_name='User',
            object_id=instance.id,
            object_repr=str(instance),
            changes=instance._changes
        )

@receiver(post_delete, sender=User)
def log_user_deletion(sender, instance, **kwargs):
    """Log user deletion"""
    AuditLog.objects.create(
        user=None,
        action='DELETE',
        model_name='User',
        object_id=instance.id,
        object_repr=str(instance),
        changes={'deleted_username': instance.username}
    )

@receiver(user_logged_in)
def track_user_login(sender, request, user, **kwargs):
    """Track user login"""
    user.last_login = timezone.now()
    user.last_login_ip = request.META.get('REMOTE_ADDR')
    user.save(update_fields=['last_login', 'last_login_ip'])
    
    # Update last activity
    user.update_last_activity()

@receiver(user_logged_out)
def track_user_logout(sender, request, user, **kwargs):
    """Track user logout"""
    if user:
        user.update_last_activity()