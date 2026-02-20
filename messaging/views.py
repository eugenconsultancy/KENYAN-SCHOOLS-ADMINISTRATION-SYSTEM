from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages as django_messages
from django.db.models import Q, Count
from django.core.paginator import Paginator
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType
from accounts.decorators import role_required
from .models import (
    Conversation, Message, Announcement, Notification,
    BroadcastList, MessageTemplate, EmailLog, SMSLog
)
from .forms import (
    ComposeMessageForm, ReplyMessageForm, AnnouncementForm,
    BroadcastListForm, MessageTemplateForm, NotificationSettingsForm,
    FilterMessagesForm
)
from .services import MessagingService, NotificationService, SMSService, EmailService
from accounts.models import User
import json

# ============== Inbox Views ==============

@login_required
def inbox(request):
    """User inbox showing conversations"""
    
    conversations = Conversation.objects.filter(
        participants=request.user
    ).annotate(
        message_count=Count('messages'),
        unread_count=Count(
            'messages',
            filter=~Q(messages__read_by=request.user) & ~Q(messages__sender=request.user)
        )
    ).order_by('-updated_at')
    
    # Pre-process conversation data for the template
    conversation_data = []
    for conversation in conversations:
        # Get the other participant (first one that's not the current user)
        other_participant = conversation.participants.exclude(id=request.user.id).first()
        
        # Get last message
        last_message = conversation.get_last_message()
        
        conversation_data.append({
            'id': conversation.id,
            'other_participant': other_participant,
            'last_message': last_message,
            'unread_count': getattr(conversation, 'unread_count', 0),
            'updated_at': conversation.updated_at,
            'participant_count': conversation.participants.count()
        })
    
    # Filter form
    form = FilterMessagesForm(request.GET)
    
    context = {
        'conversations': conversation_data,
        'form': form,
    }
    
    return render(request, 'messaging/inbox.html', context)

@login_required
def conversation_detail(request, conversation_id):
    """View a specific conversation"""
    
    conversation = get_object_or_404(
        Conversation.objects.filter(participants=request.user),
        id=conversation_id
    )
    
    # Get messages
    messages_list = conversation.messages.all().order_by('created_at')
    
    # Mark messages as read
    for msg in messages_list:
        if msg.sender != request.user:
            msg.mark_as_read(request.user)
    
    # Reply form
    if request.method == 'POST':
        form = ReplyMessageForm(request.POST, request.FILES)
        if form.is_valid():
            message = Message.objects.create(
                conversation=conversation,
                sender=request.user,
                content=form.cleaned_data['content'],
                attachment=form.cleaned_data.get('attachment')
            )
            
            # Update conversation timestamp
            conversation.save()
            
            django_messages.success(request, 'Message sent.')
            return redirect('messaging:conversation', conversation_id=conversation.id)
    else:
        form = ReplyMessageForm()
    
    # Get other participants
    other_participants = conversation.participants.exclude(id=request.user.id)
    
    context = {
        'conversation': conversation,
        'messages': messages_list,
        'form': form,
        'other_participants': other_participants,
    }
    
    return render(request, 'messaging/conversation.html', context)

@login_required
def compose_message(request):
    """Compose a new message"""
    
    if request.method == 'POST':
        form = ComposeMessageForm(request.POST, request.FILES)
        if form.is_valid():
            # Get recipients
            recipients = form.cleaned_data['recipients']
            recipient_type = form.cleaned_data['recipient_type']
            
            if recipient_type:
                if recipient_type == 'all_students':
                    recipients = User.objects.filter(role='student', is_active=True)
                elif recipient_type == 'all_teachers':
                    recipients = User.objects.filter(role='teacher', is_active=True)
                elif recipient_type == 'all_parents':
                    recipients = User.objects.filter(role='parent', is_active=True)
                elif recipient_type == 'class':
                    class_level = form.cleaned_data['class_level']
                    stream = form.cleaned_data['stream']
                    from students.models import Student
                    students = Student.objects.filter(
                        current_class=class_level,
                        stream=stream,
                        is_active=True
                    ).select_related('user')
                    recipients = [s.user for s in students]
                elif recipient_type == 'broadcast':
                    broadcast_list = form.cleaned_data['broadcast_list']
                    recipients = broadcast_list.members.all()
            
            if not recipients:
                django_messages.error(request, 'No recipients selected.')
                return redirect('messaging:compose')
            
            # Create conversation and send messages
            success = MessagingService.send_bulk_message(
                sender=request.user,
                recipients=recipients,
                subject=form.cleaned_data.get('subject', ''),
                content=form.cleaned_data['content'],
                attachment=form.cleaned_data.get('attachment')
            )
            
            if success:
                django_messages.success(request, f'Message sent to {len(recipients)} recipient(s).')
                return redirect('messaging:inbox')
            else:
                django_messages.error(request, 'Error sending message.')
    else:
        form = ComposeMessageForm()
        
        # Pre-fill recipients if user_id is provided
        user_id = request.GET.get('user')
        if user_id:
            try:
                user = User.objects.get(id=user_id)
                form.fields['recipients'].initial = [user]
            except User.DoesNotExist:
                pass
    
    return render(request, 'messaging/compose.html', {'form': form})

# ============== Announcement Views ==============

@login_required
def announcement_list(request):
    """List all announcements"""
    
    announcements = Announcement.objects.all().order_by('-publish_date')
    
    # Filter active/expired
    show = request.GET.get('show', 'active')
    now = timezone.now()
    
    if show == 'active':
        announcements = announcements.filter(
            Q(expiry_date__gte=now) | Q(expiry_date__isnull=True),
            publish_date__lte=now
        )
    elif show == 'expired':
        announcements = announcements.filter(expiry_date__lt=now)
    
    paginator = Paginator(announcements, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'show': show,
    }
    
    return render(request, 'messaging/announcement_list.html', context)

@login_required
def announcement_detail(request, announcement_id):
    """View announcement details"""
    
    announcement = get_object_or_404(Announcement, id=announcement_id)
    
    # Mark as read
    announcement.read_by.add(request.user)
    
    context = {
        'announcement': announcement,
    }
    
    return render(request, 'messaging/announcement_detail.html', context)

@login_required
@role_required(['admin', 'teacher'])
def announcement_create(request):
    """Create new announcement"""
    
    if request.method == 'POST':
        form = AnnouncementForm(request.POST, request.FILES)
        if form.is_valid():
            announcement = form.save(commit=False)
            announcement.created_by = request.user
            announcement.save()
            
            django_messages.success(request, 'Announcement created successfully.')
            return redirect('messaging:announcement_list')
    else:
        form = AnnouncementForm()
    
    return render(request, 'messaging/announcement_form.html', {
        'form': form,
        'title': 'Create Announcement'
    })

@login_required
@role_required(['admin', 'teacher'])
def announcement_edit(request, announcement_id):
    """Edit announcement"""
    
    announcement = get_object_or_404(Announcement, id=announcement_id)
    
    if request.method == 'POST':
        form = AnnouncementForm(request.POST, request.FILES, instance=announcement)
        if form.is_valid():
            form.save()
            django_messages.success(request, 'Announcement updated.')
            return redirect('messaging:announcement_detail', announcement_id=announcement.id)
    else:
        form = AnnouncementForm(instance=announcement)
    
    return render(request, 'messaging/announcement_form.html', {
        'form': form,
        'announcement': announcement,
        'title': 'Edit Announcement'
    })

@login_required
@role_required(['admin'])
def announcement_delete(request, announcement_id):
    """Delete announcement"""
    
    announcement = get_object_or_404(Announcement, id=announcement_id)
    
    if request.method == 'POST':
        announcement.delete()
        django_messages.success(request, 'Announcement deleted.')
        return redirect('messaging:announcement_list')
    
    return render(request, 'messaging/announcement_confirm_delete.html', {
        'announcement': announcement
    })

# ============== Notification Views ==============

@login_required
def notifications(request):
    """User notifications"""
    
    notifications_list = request.user.notifications.all().order_by('-created_at')
    
    # Mark all as read if requested
    if request.GET.get('mark_read'):
        notifications_list.update(is_read=True, read_at=timezone.now())
        django_messages.success(request, 'All notifications marked as read.')
        return redirect('messaging:notifications')
    
    # Pagination
    paginator = Paginator(notifications_list, 30)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'unread_count': request.user.notifications.filter(is_read=False).count(),
    }
    
    return render(request, 'messaging/notifications.html', context)

@login_required
def notification_detail(request, notification_id):
    """View notification details"""
    
    notification = get_object_or_404(Notification, id=notification_id, recipient=request.user)
    
    if not notification.is_read:
        notification.mark_as_read()
    
    context = {
        'notification': notification,
    }
    
    return render(request, 'messaging/notification_detail.html', context)

@login_required
def mark_notification_read(request, notification_id):
    """Mark notification as read (AJAX)"""
    
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        notification = get_object_or_404(Notification, id=notification_id, recipient=request.user)
        notification.mark_as_read()
        return JsonResponse({'status': 'success'})
    
    return JsonResponse({'error': 'Invalid request'}, status=400)

@login_required
def mark_all_read(request):
    """Mark all notifications as read"""
    
    request.user.notifications.filter(is_read=False).update(
        is_read=True,
        read_at=timezone.now()
    )
    
    return JsonResponse({'status': 'success'})

# ============== Broadcast List Views ==============

@login_required
@role_required(['admin'])
def broadcast_list_list(request):
    """List broadcast lists"""
    
    lists = BroadcastList.objects.all().order_by('name')
    
    context = {
        'lists': lists,
    }
    
    return render(request, 'messaging/broadcast_list_list.html', context)

@login_required
@role_required(['admin'])
def broadcast_list_create(request):
    """Create broadcast list"""
    
    if request.method == 'POST':
        form = BroadcastListForm(request.POST)
        if form.is_valid():
            broadcast_list = form.save(commit=False)
            broadcast_list.created_by = request.user
            broadcast_list.save()
            broadcast_list.update_members()
            
            django_messages.success(request, 'Broadcast list created.')
            return redirect('messaging:broadcast_list_list')
    else:
        form = BroadcastListForm()
    
    return render(request, 'messaging/broadcast_list_form.html', {
        'form': form,
        'title': 'Create Broadcast List'
    })

@login_required
@role_required(['admin'])
def broadcast_list_edit(request, list_id):
    """Edit broadcast list"""
    
    broadcast_list = get_object_or_404(BroadcastList, id=list_id)
    
    if request.method == 'POST':
        form = BroadcastListForm(request.POST, instance=broadcast_list)
        if form.is_valid():
            form.save()
            broadcast_list.update_members()
            django_messages.success(request, 'Broadcast list updated.')
            return redirect('messaging:broadcast_list_list')
    else:
        form = BroadcastListForm(instance=broadcast_list)
    
    return render(request, 'messaging/broadcast_list_form.html', {
        'form': form,
        'broadcast_list': broadcast_list,
        'title': 'Edit Broadcast List'
    })

@login_required
@role_required(['admin'])
def broadcast_list_delete(request, list_id):
    """Delete broadcast list"""
    
    broadcast_list = get_object_or_404(BroadcastList, id=list_id)
    
    if request.method == 'POST':
        broadcast_list.delete()
        django_messages.success(request, 'Broadcast list deleted.')
        return redirect('messaging:broadcast_list_list')
    
    return render(request, 'messaging/broadcast_list_confirm_delete.html', {
        'broadcast_list': broadcast_list
    })

@login_required
@role_required(['admin'])
def broadcast_list_members(request, list_id):
    """View broadcast list members"""
    
    broadcast_list = get_object_or_404(BroadcastList, id=list_id)
    members = broadcast_list.members.all().order_by('username')
    
    context = {
        'broadcast_list': broadcast_list,
        'members': members,
    }
    
    return render(request, 'messaging/broadcast_list_members.html', context)

# ============== Template Views ==============

@login_required
def template_list(request):
    """List message templates"""
    
    templates = MessageTemplate.objects.all().order_by('name')
    
    context = {
        'templates': templates,
    }
    
    return render(request, 'messaging/template_list.html', context)

@login_required
def template_create(request):
    """Create message template"""
    
    if request.method == 'POST':
        form = MessageTemplateForm(request.POST)
        if form.is_valid():
            template = form.save(commit=False)
            template.created_by = request.user
            template.save()
            django_messages.success(request, 'Template created.')
            return redirect('messaging:template_list')
    else:
        form = MessageTemplateForm()
    
    return render(request, 'messaging/template_form.html', {
        'form': form,
        'title': 'Create Template'
    })

@login_required
def template_edit(request, template_id):
    """Edit message template"""
    
    template = get_object_or_404(MessageTemplate, id=template_id)
    
    if request.method == 'POST':
        form = MessageTemplateForm(request.POST, instance=template)
        if form.is_valid():
            form.save()
            django_messages.success(request, 'Template updated.')
            return redirect('messaging:template_list')
    else:
        form = MessageTemplateForm(instance=template)
    
    return render(request, 'messaging/template_form.html', {
        'form': form,
        'template': template,
        'title': 'Edit Template'
    })

@login_required
def template_delete(request, template_id):
    """Delete message template"""
    
    template = get_object_or_404(MessageTemplate, id=template_id)
    
    if request.method == 'POST':
        template.delete()
        django_messages.success(request, 'Template deleted.')
        return redirect('messaging:template_list')
    
    return render(request, 'messaging/template_confirm_delete.html', {
        'template': template
    })

@login_required
def template_preview(request, template_id):
    """Preview template with sample data"""
    
    template = get_object_or_404(MessageTemplate, id=template_id)
    
    # Sample context
    context = {
        'student_name': 'John Doe',
        'parent_name': 'Jane Doe',
        'class_name': 'Form 1 East',
        'amount': '10,000',
        'due_date': '2024-12-31',
        'percentage': '85%',
        'grade': 'A',
    }
    
    rendered = template.render(context)
    
    return JsonResponse(rendered)

# ============== Settings Views ==============

@login_required
def notification_settings(request):
    """User notification settings"""
    
    if request.method == 'POST':
        form = NotificationSettingsForm(request.POST)
        if form.is_valid():
            # Save settings to user profile (you'd need to add these fields to User model)
            # For now, just show success message
            django_messages.success(request, 'Settings saved.')
            return redirect('messaging:notification_settings')
    else:
        # Load current settings (default values for now)
        form = NotificationSettingsForm()
    
    return render(request, 'messaging/notification_settings.html', {'form': form})

# ============== API Views ==============

@login_required
def get_unread_count(request):
    """Get unread count for notifications and messages"""
    
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        unread_notifications = request.user.notifications.filter(is_read=False).count()
        
        unread_messages = Message.objects.filter(
            conversation__participants=request.user
        ).exclude(
            sender=request.user
        ).exclude(
            read_by=request.user
        ).count()
        
        return JsonResponse({
            'notifications': unread_notifications,
            'messages': unread_messages,
            'total': unread_notifications + unread_messages
        })
    
    return JsonResponse({'error': 'Invalid request'}, status=400)

@login_required
def search_users(request):
    """Search users for messaging"""
    
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        query = request.GET.get('q', '')
        
        users = User.objects.filter(
            Q(username__icontains=query) |
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(email__icontains=query)
        ).filter(is_active=True).exclude(id=request.user.id)[:20]
        
        data = [{
            'id': user.id,
            'text': f"{user.get_full_name()} ({user.get_role_display()})",
            'username': user.username,
            'email': user.email,
            'role': user.get_role_display(),
        } for user in users]
        
        return JsonResponse({'results': data})
    
    return JsonResponse({'error': 'Invalid request'}, status=400)