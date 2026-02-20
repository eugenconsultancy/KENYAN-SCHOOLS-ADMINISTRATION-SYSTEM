from django import forms
from django.core.exceptions import ValidationError
from .models import (
    Conversation, Message, Announcement, Notification,
    BroadcastList, MessageTemplate, EmailLog, SMSLog
)
from accounts.models import User
from students.models import Student
from django.utils import timezone
import datetime

class ComposeMessageForm(forms.Form):
    """Form for composing new messages"""
    
    recipients = forms.ModelMultipleChoiceField(
        queryset=User.objects.filter(is_active=True),
        widget=forms.SelectMultiple(attrs={'class': 'select2', 'style': 'width: 100%'}),
        required=False
    )
    recipient_type = forms.ChoiceField(
        choices=[
            ('', 'Select Recipient Type'),
            ('all_students', 'All Students'),
            ('all_teachers', 'All Teachers'),
            ('all_parents', 'All Parents'),
            ('class', 'Specific Class'),
            ('broadcast', 'Broadcast List'),
        ],
        required=False
    )
    class_level = forms.ChoiceField(
        choices=[('', 'Select Class')] + list(Student.CLASS_LEVELS),
        required=False
    )
    stream = forms.ChoiceField(
        choices=[('', 'Select Stream')] + list(Student.STREAMS),
        required=False
    )
    broadcast_list = forms.ModelChoiceField(
        queryset=BroadcastList.objects.all(),
        required=False
    )
    
    subject = forms.CharField(max_length=200, required=False)
    content = forms.CharField(widget=forms.Textarea(attrs={'rows': 6}))
    attachment = forms.FileField(required=False)
    
    def clean(self):
        cleaned_data = super().clean()
        recipients = cleaned_data.get('recipients')
        recipient_type = cleaned_data.get('recipient_type')
        
        if not recipients and not recipient_type:
            raise ValidationError('Please select recipients.')
        
        return cleaned_data

class ReplyMessageForm(forms.Form):
    """Form for replying to messages"""
    
    content = forms.CharField(widget=forms.Textarea(attrs={'rows': 4}))
    attachment = forms.FileField(required=False)

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
            'publish_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'expiry_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'content': forms.Textarea(attrs={'rows': 6}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['target_class_level'].required = False
        self.fields['target_stream'].required = False
        self.fields['expiry_date'].required = False
        self.fields['attachment'].required = False
        
        # Set initial publish date to now
        self.fields['publish_date'].initial = timezone.now()
    
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
            'description': forms.Textarea(attrs={'rows': 3}),
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
            'content': forms.Textarea(attrs={'rows': 6}),
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
    
    search = forms.CharField(max_length=100, required=False, widget=forms.TextInput(attrs={
        'placeholder': 'Search messages...'
    }))
    date_from = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))
    date_to = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))
    unread_only = forms.BooleanField(required=False)