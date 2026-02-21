from django import forms
from django.core.exceptions import ValidationError
from .models import (
    Conversation, Message, Announcement, Notification,
    BroadcastList, MessageTemplate
)
from accounts.models import User
from students.models import Student
import datetime
from django.utils import timezone

class ComposeMessageForm(forms.Form):
    """Form for composing new messages"""
    
    recipient_type = forms.ChoiceField(
        choices=[
            ('individual', 'Individual'),
            ('all_students', 'All Students'),
            ('all_teachers', 'All Teachers'),
            ('all_parents', 'All Parents'),
            ('class', 'Specific Class'),
            ('broadcast', 'Broadcast List'),
        ],
        required=True,
        initial='individual',
        widget=forms.Select(attrs={'class': 'hidden'})  # Hidden as we use buttons
    )
    
    recipients = forms.ModelMultipleChoiceField(
        queryset=User.objects.filter(is_active=True).order_by('first_name', 'last_name'),
        required=False,
        widget=forms.SelectMultiple(attrs={'class': 'select2', 'style': 'width: 100%'})
    )
    
    class_level = forms.ChoiceField(
        choices=[('', 'Select Class')] + [(1, 'Form 1'), (2, 'Form 2'), (3, 'Form 3'), (4, 'Form 4')],
        required=False,
        widget=forms.Select(attrs={'class': 'glass-input'})
    )
    
    stream = forms.ChoiceField(
        choices=[('', 'Select Stream')] + [('East', 'East'), ('West', 'West'), ('North', 'North'), ('South', 'South')],
        required=False,
        widget=forms.Select(attrs={'class': 'glass-input'})
    )
    
    broadcast_list = forms.ModelChoiceField(
        queryset=BroadcastList.objects.all(),
        required=False,
        widget=forms.Select(attrs={'class': 'glass-input'})
    )
    
    subject = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={'class': 'glass-input', 'placeholder': 'Enter message subject'})
    )
    
    content = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'glass-input', 'rows': 6, 'placeholder': 'Type your message here...'}),
        required=True
    )
    
    attachment = forms.FileField(
        required=False,
        widget=forms.FileInput(attrs={'class': 'glass-input'})
    )
    
    def clean(self):
        cleaned_data = super().clean()
        recipient_type = cleaned_data.get('recipient_type')
        
        if recipient_type == 'individual' and not cleaned_data.get('recipients'):
            raise ValidationError('Please select at least one recipient.')
        elif recipient_type == 'class':
            class_level = cleaned_data.get('class_level')
            stream = cleaned_data.get('stream')
            if not class_level or not stream:
                raise ValidationError('Please select both class level and stream.')
        elif recipient_type == 'broadcast' and not cleaned_data.get('broadcast_list'):
            raise ValidationError('Please select a broadcast list.')
        
        return cleaned_data

class ReplyMessageForm(forms.Form):
    """Form for replying to messages"""
    
    content = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'glass-input', 'rows': 4, 'placeholder': 'Type your reply...'}),
        required=True
    )
    attachment = forms.FileField(
        required=False,
        widget=forms.FileInput(attrs={'class': 'glass-input'})
    )

class AnnouncementForm(forms.ModelForm):
    """Form for creating announcements"""
    
    class Meta:
        model = Announcement
        fields = [
            'title', 'content', 'audience_type', 'target_class_level',
            'target_stream', 'priority', 'publish_date', 'expiry_date',
            'attachment'
        ]
        widgets = {
            'publish_date': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'glass-input'}),
            'expiry_date': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'glass-input'}),
            'content': forms.Textarea(attrs={'class': 'glass-input', 'rows': 6}),
            'title': forms.TextInput(attrs={'class': 'glass-input', 'placeholder': 'Enter announcement title'}),
            'audience_type': forms.Select(attrs={'class': 'glass-input', 'id': 'audienceType'}),
            'target_class_level': forms.Select(attrs={'class': 'glass-input', 'id': 'targetClass'}),
            'target_stream': forms.Select(attrs={'class': 'glass-input', 'id': 'targetStream'}),
            'priority': forms.Select(attrs={'class': 'glass-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['target_class_level'].required = False
        self.fields['target_stream'].required = False
        self.fields['expiry_date'].required = False
        self.fields['attachment'].required = False
        
        # Set initial publish date to now
        self.fields['publish_date'].initial = timezone.now().strftime('%Y-%m-%dT%H:%M')
    
    def clean(self):
        cleaned_data = super().clean()
        audience_type = cleaned_data.get('audience_type')
        target_class = cleaned_data.get('target_class_level')
        
        if audience_type == 'class' and not target_class:
            raise ValidationError('Please select a class for class-specific announcements.')
        
        publish_date = cleaned_data.get('publish_date')
        expiry_date = cleaned_data.get('expiry_date')
        
        if expiry_date and publish_date and expiry_date <= publish_date:
            raise ValidationError('Expiry date must be after publish date.')
        
        return cleaned_data

class BroadcastListForm(forms.ModelForm):
    """Form for creating broadcast lists"""
    
    class Meta:
        model = BroadcastList
        fields = ['name', 'description', 'filter_by_role', 'filter_by_class', 'filter_by_stream']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'glass-input', 'placeholder': 'Enter list name'}),
            'description': forms.Textarea(attrs={'class': 'glass-input', 'rows': 3, 'placeholder': 'Describe the purpose of this list'}),
            'filter_by_role': forms.Select(attrs={'class': 'glass-input', 'id': 'filterRole'}),
            'filter_by_class': forms.Select(attrs={'class': 'glass-input', 'id': 'filterClass'}),
            'filter_by_stream': forms.Select(attrs={'class': 'glass-input', 'id': 'filterStream'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['filter_by_role'].required = False
        self.fields['filter_by_class'].required = False
        self.fields['filter_by_stream'].required = False
        self.fields['description'].required = False

class MessageTemplateForm(forms.ModelForm):
    """Form for message templates"""
    
    class Meta:
        model = MessageTemplate
        fields = ['name', 'template_type', 'subject', 'content', 'variables']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'glass-input', 'placeholder': 'e.g., Fee Reminder, Exam Notification'}),
            'template_type': forms.Select(attrs={'class': 'glass-input'}),
            'subject': forms.TextInput(attrs={'class': 'glass-input', 'placeholder': 'Subject with {{ variables }}'}),
            'content': forms.Textarea(attrs={'class': 'glass-input font-mono', 'rows': 10}),
            'variables': forms.HiddenInput(),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['variables'].required = False

class NotificationSettingsForm(forms.Form):
    """Form for notification settings"""
    
    email_notifications = forms.BooleanField(required=False, initial=True)
    sms_notifications = forms.BooleanField(required=False, initial=False)
    push_notifications = forms.BooleanField(required=False, initial=True)
    
    notify_messages = forms.BooleanField(required=False, initial=True)
    notify_announcements = forms.BooleanField(required=False, initial=True)
    notify_attendance = forms.BooleanField(required=False, initial=True)
    notify_payments = forms.BooleanField(required=False, initial=True)
    notify_results = forms.BooleanField(required=False, initial=True)

class FilterMessagesForm(forms.Form):
    """Form for filtering messages"""
    
    search = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'class': 'glass-input', 'placeholder': 'Search messages...'})
    )
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'glass-input', 'type': 'date'})
    )
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'glass-input', 'type': 'date'})
    )
    unread_only = forms.BooleanField(required=False)