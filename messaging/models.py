from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from accounts.models import User
from students.models import Student
from django.utils import timezone
from teachers.models import Teacher
import datetime

class Conversation(models.Model):
    """Conversation between users"""
    
    participants = models.ManyToManyField(User, related_name='conversations')
    subject = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-updated_at']
    
    def __str__(self):
        participants_str = ", ".join([u.get_full_name() or u.username for u in self.participants.all()[:3]])
        if self.participants.count() > 3:
            participants_str += f" and {self.participants.count() - 3} others"
        return f"Conversation: {participants_str}"
    
    def get_last_message(self):
        return self.messages.order_by('-created_at').first()
    
    def get_unread_count(self, user):
        return self.messages.filter(read_by__isnull=True).exclude(sender=user).count()

class Message(models.Model):
    """Individual message in a conversation"""
    
    MESSAGE_TYPES = [
        ('text', 'Text'),
        ('image', 'Image'),
        ('file', 'File'),
        ('announcement', 'Announcement'),
    ]
    
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    message_type = models.CharField(max_length=20, choices=MESSAGE_TYPES, default='text')
    
    # Content
    content = models.TextField()
    
    # Attachments
    attachment = models.FileField(upload_to='messages/attachments/', null=True, blank=True)
    attachment_name = models.CharField(max_length=255, blank=True)
    
    # Read receipts
    read_by = models.ManyToManyField(User, related_name='read_messages', blank=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['created_at']
    
    def __str__(self):
        return f"Message from {self.sender.get_full_name()} at {self.created_at}"
    
    def mark_as_read(self, user):
        if user not in self.read_by.all():
            self.read_by.add(user)

class Announcement(models.Model):
    """School-wide announcements"""
    
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('normal', 'Normal'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]
    
    AUDIENCE_CHOICES = [
        ('all', 'Everyone'),
        ('students', 'All Students'),
        ('teachers', 'All Teachers'),
        ('parents', 'All Parents'),
        ('staff', 'All Staff'),
        ('class', 'Specific Class'),
        ('individual', 'Specific Individuals'),
    ]
    
    title = models.CharField(max_length=200)
    content = models.TextField()
    
    # Audience
    audience_type = models.CharField(max_length=20, choices=AUDIENCE_CHOICES, default='all')
    target_class_level = models.IntegerField(choices=Student.CLASS_LEVELS, null=True, blank=True)
    target_stream = models.CharField(max_length=10, choices=Student.STREAMS, null=True, blank=True)
    
    # Priority
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='normal')
    
    # Scheduling
    publish_date = models.DateTimeField()
    expiry_date = models.DateTimeField(null=True, blank=True)
    
    # Attachments
    attachment = models.FileField(upload_to='announcements/', null=True, blank=True)
    
    # Metadata
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_announcements')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Read tracking
    read_by = models.ManyToManyField(User, related_name='read_announcements', blank=True)
    
    class Meta:
        ordering = ['-publish_date', '-priority']
    
    def __str__(self):
        return self.title
    
    def is_active(self):
        now = timezone.now()
        if self.expiry_date:
            return self.publish_date <= now <= self.expiry_date
        return self.publish_date <= now
    
    def get_audience_display(self):
        if self.audience_type == 'class' and self.target_class_level:
            stream = f" {self.target_stream}" if self.target_stream else ""
            return f"Form {self.target_class_level}{stream}"
        return self.get_audience_type_display()

class Notification(models.Model):
    """In-app notifications"""
    
    NOTIFICATION_TYPES = [
        ('info', 'Information'),
        ('success', 'Success'),
        ('warning', 'Warning'),
        ('error', 'Error'),
        ('message', 'New Message'),
        ('announcement', 'Announcement'),
        ('attendance', 'Attendance'),
        ('payment', 'Payment'),
        ('result', 'Result'),
    ]
    
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='messaging_notifications')
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES, default='info')
    
    # Content
    title = models.CharField(max_length=200)
    message = models.TextField()
    
    # Link (for click action)
    link = models.CharField(max_length=200, blank=True)
    
    # Read status
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    
    # For grouping
    group_key = models.CharField(max_length=100, blank=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', '-created_at']),
            models.Index(fields=['recipient', 'is_read']),
        ]
    
    def __str__(self):
        return f"{self.recipient.username} - {self.title}"
    
    def mark_as_read(self):
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save()

class BroadcastList(models.Model):
    """Groups for broadcasting messages"""
    
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    
    # Members (can be students, teachers, or parents)
    members = models.ManyToManyField(User, related_name='broadcast_lists', blank=True)
    
    # Dynamic filters (for auto-updating lists)
    filter_by_role = models.CharField(max_length=20, choices=User.ROLE_CHOICES, null=True, blank=True)
    filter_by_class = models.IntegerField(choices=Student.CLASS_LEVELS, null=True, blank=True)
    filter_by_stream = models.CharField(max_length=10, choices=Student.STREAMS, null=True, blank=True)
    
    # Metadata
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return self.name
    
    def update_members(self):
        """Update members based on filters"""
        if not (self.filter_by_role or self.filter_by_class):
            return
        
        users = User.objects.filter(is_active=True)
        
        if self.filter_by_role:
            users = users.filter(role=self.filter_by_role)
        
        if self.filter_by_class and self.filter_by_role == 'student':
            # Filter students by class
            student_ids = Student.objects.filter(
                current_class=self.filter_by_class,
                stream=self.filter_by_stream if self.filter_by_stream else None,
                is_active=True
            ).values_list('user_id', flat=True)
            users = users.filter(id__in=student_ids)
        
        self.members.set(users)

class MessageTemplate(models.Model):
    """Pre-defined message templates"""
    
    TEMPLATE_TYPES = [
        ('general', 'General'),
        ('attendance', 'Attendance'),
        ('fee', 'Fee Reminder'),
        ('meeting', 'Meeting'),
        ('event', 'Event'),
        ('result', 'Results'),
        ('holiday', 'Holiday'),
    ]
    
    name = models.CharField(max_length=100)
    template_type = models.CharField(max_length=20, choices=TEMPLATE_TYPES, default='general')
    subject = models.CharField(max_length=200)
    content = models.TextField()
    
    # Variables (for dynamic content)
    variables = models.JSONField(default=list, blank=True)
    
    # Metadata
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return self.name
    
    def render(self, context):
        """Render template with context variables"""
        content = self.content
        subject = self.subject
        
        for key, value in context.items():
            placeholder = f"{{{{ {key} }}}}"
            content = content.replace(placeholder, str(value))
            subject = subject.replace(placeholder, str(value))
        
        return {
            'subject': subject,
            'content': content
        }

class EmailLog(models.Model):
    """Log of sent emails"""
    
    STATUS_CHOICES = [
        ('sent', 'Sent'),
        ('delivered', 'Delivered'),
        ('failed', 'Failed'),
        ('opened', 'Opened'),
    ]
    
    recipient = models.EmailField()
    subject = models.CharField(max_length=200)
    body = models.TextField()
    
    # Related objects
    content_type = models.ForeignKey(ContentType, on_delete=models.SET_NULL, null=True, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    related_object = GenericForeignKey('content_type', 'object_id')
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='sent')
    error_message = models.TextField(blank=True)
    
    # Tracking
    opened_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-sent_at']
    
    def __str__(self):
        return f"Email to {self.recipient} - {self.subject}"

class SMSLog(models.Model):
    """Log of sent SMS messages"""
    
    STATUS_CHOICES = [
        ('sent', 'Sent'),
        ('delivered', 'Delivered'),
        ('failed', 'Failed'),
    ]
    
    recipient = models.CharField(max_length=15)
    message = models.TextField()
    
    # Related objects
    content_type = models.ForeignKey(ContentType, on_delete=models.SET_NULL, null=True, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    related_object = GenericForeignKey('content_type', 'object_id')
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='sent')
    error_message = models.TextField(blank=True)
    
    # Provider info
    provider_message_id = models.CharField(max_length=100, blank=True)
    
    sent_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-sent_at']
    
    def __str__(self):
        return f"SMS to {self.recipient}"