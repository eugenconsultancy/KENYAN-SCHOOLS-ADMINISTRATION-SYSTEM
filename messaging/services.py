"""
Services module for Messaging app
Handles business logic for messaging operations with real-time WebSocket support
"""

from django.db.models import Count, Q
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .models import (
    Conversation, Message, Notification, Announcement,
    EmailLog, SMSLog
)
from accounts.models import User
import json

class MessagingService:
    """Service for messaging operations with real-time updates"""
    
    @staticmethod
    def get_or_create_conversation(participants):
        """Get or create a conversation between users"""
        
        if len(participants) < 2:
            return None
        
        # Sort participants for consistent query
        participant_ids = sorted([p.id for p in participants])
        
        # Find existing conversation with exactly these participants
        conversations = Conversation.objects.annotate(
            count=Count('participants')
        ).filter(
            count=len(participant_ids)
        )
        
        for participant_id in participant_ids:
            conversations = conversations.filter(participants__id=participant_id)
        
        conversation = conversations.first()
        
        if not conversation:
            conversation = Conversation.objects.create()
            conversation.participants.set(participants)
        
        return conversation
    
    @staticmethod
    def send_message(sender, recipients, content, subject='', attachment=None):
        """Send a message to one or more recipients with real-time notification"""
        
        if not isinstance(recipients, list):
            recipients = [recipients]
        
        # Add sender to participants
        all_participants = list(set([sender] + recipients))
        
        # Get or create conversation
        conversation = MessagingService.get_or_create_conversation(all_participants)
        
        if not conversation:
            return None
        
        # Create message
        message = Message.objects.create(
            conversation=conversation,
            sender=sender,
            content=content,
            attachment=attachment
        )
        
        channel_layer = get_channel_layer()
        
        # Create notifications and broadcast real-time updates
        for recipient in recipients:
            if recipient != sender:
                # Create database notification
                notification = Notification.objects.create(
                    recipient=recipient,
                    notification_type='message',
                    title=f"New message from {sender.get_full_name()}",
                    message=content[:100] + ('...' if len(content) > 100 else ''),
                    link=f"/messaging/conversation/{conversation.id}/"
                )
                
                # Send real-time notification via WebSocket
                async_to_sync(channel_layer.group_send)(
                    f'user_{recipient.id}_notifications',
                    {
                        'type': 'notification_message',
                        'notification': {
                            'id': notification.id,
                            'title': notification.title,
                            'message': notification.message,
                            'link': notification.link,
                            'created_at': notification.created_at.isoformat()
                        }
                    }
                )
                
                # Send new message notification to recipient's conversation group
                async_to_sync(channel_layer.group_send)(
                    f'user_{recipient.id}_conversations',
                    {
                        'type': 'conversation_message',
                        'message': {
                            'id': message.id,
                            'content': message.content[:50],
                            'sender': sender.get_full_name(),
                            'sender_id': sender.id,
                            'conversation_id': conversation.id,
                            'timestamp': message.created_at.isoformat(),
                            'is_read': False
                        },
                        'conversation_id': conversation.id,
                        'sender': sender.get_full_name(),
                        'timestamp': message.created_at.isoformat()
                    }
                )
        
        # Broadcast to conversation group for real-time chat
        async_to_sync(channel_layer.group_send)(
            f'conversation_{conversation.id}',
            {
                'type': 'chat_message',
                'message': {
                    'id': message.id,
                    'content': message.content,
                    'sender': sender.get_full_name(),
                    'sender_id': sender.id,
                    'timestamp': message.created_at.isoformat(),
                    'attachment': message.attachment.url if message.attachment else None
                }
            }
        )
        
        # Update conversation list for all participants
        for participant in all_participants:
            async_to_sync(channel_layer.group_send)(
                f'user_{participant.id}_conversations',
                {
                    'type': 'conversation_updated',
                    'conversation_id': conversation.id
                }
            )
        
        return message
    
    @staticmethod
    def send_bulk_message(sender, recipients, subject, content, attachment=None):
        """Send message to multiple recipients (creates separate conversations)"""
        
        sent_count = 0
        
        for recipient in recipients:
            if recipient != sender:
                # Create individual conversation for each recipient
                message = MessagingService.send_message(
                    sender=sender,
                    recipients=[recipient],
                    content=content,
                    attachment=attachment
                )
                if message:
                    sent_count += 1
        
        return sent_count
    
    @staticmethod
    def mark_as_read(conversation_id, user):
        """Mark all messages in a conversation as read"""
        
        messages = Message.objects.filter(
            conversation_id=conversation_id
        ).exclude(
            sender=user
        ).exclude(
            read_by=user
        )
        
        for message in messages:
            message.mark_as_read(user)
        
        # Broadcast read receipts
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'conversation_{conversation_id}',
            {
                'type': 'read_receipt',
                'user_id': user.id,
                'user_name': user.get_full_name()
            }
        )
        
        return messages.count()
    
    @staticmethod
    def search_messages(user, query):
        """Search messages in user's conversations"""
        
        return Message.objects.filter(
            Q(conversation__participants=user),
            Q(content__icontains=query)
        ).distinct().order_by('-created_at')

class NotificationService:
    """Service for creating notifications with real-time updates"""
    
    @staticmethod
    def create_notification(recipient, notification_type, title, message, link='', group_key=''):
        """Create a single notification with real-time push"""
        
        notification = Notification.objects.create(
            recipient=recipient,
            notification_type=notification_type,
            title=title,
            message=message,
            link=link,
            group_key=group_key
        )
        
        # Send real-time notification via WebSocket
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'user_{recipient.id}_notifications',
            {
                'type': 'notification_message',
                'notification': {
                    'id': notification.id,
                    'title': notification.title,
                    'message': notification.message,
                    'link': notification.link,
                    'type': notification_type,
                    'created_at': notification.created_at.isoformat()
                }
            }
        )
        
        return notification
    
    @staticmethod
    def create_bulk_notifications(recipients, notification_type, title, message, link='', group_key=''):
        """Create notifications for multiple recipients with real-time pushes"""
        
        notifications = []
        channel_layer = get_channel_layer()
        
        for recipient in recipients:
            notification = Notification(
                recipient=recipient,
                notification_type=notification_type,
                title=title,
                message=message,
                link=link,
                group_key=group_key
            )
            notifications.append(notification)
        
        # Bulk create
        created_notifications = Notification.objects.bulk_create(notifications)
        
        # Send real-time notifications
        for notification in created_notifications:
            async_to_sync(channel_layer.group_send)(
                f'user_{notification.recipient.id}_notifications',
                {
                    'type': 'notification_message',
                    'notification': {
                        'id': notification.id,
                        'title': notification.title,
                        'message': notification.message,
                        'link': notification.link,
                        'type': notification_type,
                        'created_at': notification.created_at.isoformat()
                    }
                }
            )
        
        return created_notifications
    
    @staticmethod
    def mark_as_read(notification_id, user):
        """Mark a notification as read and broadcast update"""
        
        try:
            notification = Notification.objects.get(id=notification_id, recipient=user)
            notification.mark_as_read()
            
            # Broadcast unread count update
            channel_layer = get_channel_layer()
            unread_count = Notification.objects.filter(recipient=user, is_read=False).count()
            
            async_to_sync(channel_layer.group_send)(
                f'user_{user.id}_notifications',
                {
                    'type': 'unread_count',
                    'count': unread_count
                }
            )
            
            return True
        except Notification.DoesNotExist:
            return False
    
    @staticmethod
    def mark_all_as_read(user):
        """Mark all notifications as read for a user"""
        
        updated = Notification.objects.filter(recipient=user, is_read=False).update(
            is_read=True,
            read_at=timezone.now()
        )
        
        # Broadcast update
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'user_{user.id}_notifications',
            {
                'type': 'unread_count',
                'count': 0
            }
        )
        
        return updated
    
    @staticmethod
    def notify_announcement(announcement):
        """Create notifications for a new announcement with real-time push"""
        
        # Determine recipients based on audience
        if announcement.audience_type == 'all':
            recipients = User.objects.filter(is_active=True)
        elif announcement.audience_type == 'students':
            recipients = User.objects.filter(role='student', is_active=True)
        elif announcement.audience_type == 'teachers':
            recipients = User.objects.filter(role='teacher', is_active=True)
        elif announcement.audience_type == 'parents':
            recipients = User.objects.filter(role='parent', is_active=True)
        elif announcement.audience_type == 'staff':
            recipients = User.objects.filter(
                role__in=['admin', 'accountant', 'librarian'],
                is_active=True
            )
        elif announcement.audience_type == 'class' and announcement.target_class_level:
            from students.models import Student
            students = Student.objects.filter(
                current_class=announcement.target_class_level
            )
            if announcement.target_stream:
                students = students.filter(stream=announcement.target_stream)
            recipients = [s.user for s in students if s.user]
        else:
            return 0
        
        # Create notifications
        notifications = []
        channel_layer = get_channel_layer()
        
        for recipient in recipients:
            notification = Notification(
                recipient=recipient,
                notification_type='announcement',
                title=announcement.title,
                message=announcement.content[:100] + ('...' if len(announcement.content) > 100 else ''),
                link=f"/messaging/announcements/{announcement.id}/"
            )
            notifications.append(notification)
        
        # Bulk create
        created_notifications = Notification.objects.bulk_create(notifications)
        
        # Send real-time notifications
        for notification in created_notifications:
            async_to_sync(channel_layer.group_send)(
                f'user_{notification.recipient.id}_notifications',
                {
                    'type': 'notification_message',
                    'notification': {
                        'id': notification.id,
                        'title': notification.title,
                        'message': notification.message,
                        'link': notification.link,
                        'type': 'announcement',
                        'created_at': notification.created_at.isoformat()
                    }
                }
            )
        
        return len(created_notifications)
    
    @staticmethod
    def clear_old_notifications(days=30):
        """Delete notifications older than specified days"""
        
        cutoff = timezone.now() - timezone.timedelta(days=days)
        return Notification.objects.filter(created_at__lt=cutoff, is_read=True).delete()

class EmailService:
    """Service for sending emails"""
    
    @staticmethod
    def send_email(recipient, subject, body, related_object=None):
        """Send an email"""
        
        # Create log entry
        log = EmailLog.objects.create(
            recipient=recipient,
            subject=subject,
            body=body,
            status='sent'
        )
        
        if related_object:
            content_type = ContentType.objects.get_for_model(related_object)
            log.content_type = content_type
            log.object_id = related_object.id
            log.save()
        
        # TODO: Integrate with actual email service (e.g., SendGrid, Mailgun)
        # For now, just log it
        print(f"Email to {recipient}: {subject}")
        
        return log
    
    @staticmethod
    def send_bulk_emails(recipients, subject, body, related_object=None):
        """Send emails to multiple recipients"""
        
        logs = []
        for recipient in recipients:
            log = EmailService.send_email(recipient, subject, body, related_object)
            logs.append(log)
        
        return logs

class SMSService:
    """Service for sending SMS messages"""
    
    @staticmethod
    def send_sms(phone_number, message, related_object=None):
        """Send an SMS"""
        
        # Create log entry
        log = SMSLog.objects.create(
            recipient=phone_number,
            message=message,
            status='sent'
        )
        
        if related_object:
            content_type = ContentType.objects.get_for_model(related_object)
            log.content_type = content_type
            log.object_id = related_object.id
            log.save()
        
        # TODO: Integrate with SMS gateway (e.g., Africa's Talking, Twilio)
        # For now, just log it
        print(f"SMS to {phone_number}: {message}")
        
        return log
    
    @staticmethod
    def send_bulk_sms(phone_numbers, message, related_object=None):
        """Send SMS to multiple recipients"""
        
        logs = []
        for phone in phone_numbers:
            log = SMSService.send_sms(phone, message, related_object)
            logs.append(log)
        
        return logs
    
    @staticmethod
    def send_attendance_sms(student, date, status):
        """Send attendance notification SMS to parent"""
        
        if not student.parent_phone:
            return None
        
        message = f"Dear Parent, your child {student.get_full_name()} was marked {status} on {date}. Please contact the school for more information."
        
        return SMSService.send_sms(
            phone_number=student.parent_phone,
            message=message,
            related_object=student
        )

class AnnouncementService:
    """Service for announcement operations"""
    
    @staticmethod
    def get_active_announcements(user):
        """Get active announcements for a user"""
        
        now = timezone.now()
        
        announcements = Announcement.objects.filter(
            Q(expiry_date__gte=now) | Q(expiry_date__isnull=True),
            publish_date__lte=now
        )
        
        # Filter by audience
        if user.role == 'student':
            from students.models import Student
            try:
                student = user.student_profile
                announcements = announcements.filter(
                    Q(audience_type='all') |
                    Q(audience_type='students') |
                    Q(audience_type='class', target_class_level=student.current_class)
                )
                if student.stream:
                    announcements = announcements.filter(
                        Q(target_stream__isnull=True) |
                        Q(target_stream=student.stream)
                    )
            except:
                announcements = announcements.filter(audience_type='all')
        
        elif user.role == 'teacher':
            announcements = announcements.filter(
                Q(audience_type='all') |
                Q(audience_type='teachers') |
                Q(audience_type='staff')
            )
        
        elif user.role == 'parent':
            announcements = announcements.filter(
                Q(audience_type='all') |
                Q(audience_type='parents')
            )
        
        else:  # admin, accountant, etc.
            announcements = announcements.filter(
                Q(audience_type='all') |
                Q(audience_type='staff')
            )
        
        return announcements.order_by('-priority', '-publish_date')
    
    @staticmethod
    def mark_as_read(announcement, user):
        """Mark announcement as read by user"""
        
        announcement.read_by.add(user)
        
        # Optional: Broadcast read status
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'user_{user.id}_notifications',
            {
                'type': 'announcement_read',
                'announcement_id': announcement.id
            }
        )

class TypingService:
    """Service for handling typing indicators"""
    
    @staticmethod
    def send_typing_indicator(conversation_id, user, is_typing):
        """Send typing indicator to conversation participants"""
        
        channel_layer = get_channel_layer()
        
        async_to_sync(channel_layer.group_send)(
            f'conversation_{conversation_id}',
            {
                'type': 'typing_indicator',
                'user_id': user.id,
                'user_name': user.get_full_name(),
                'is_typing': is_typing
            }
        )

class PresenceService:
    """Service for handling user presence (online/offline)"""
    
    @staticmethod
    def user_online(user):
        """Mark user as online and broadcast to relevant conversations"""
        
        # Get all conversations where user is a participant
        conversations = Conversation.objects.filter(participants=user)
        
        channel_layer = get_channel_layer()
        
        for conversation in conversations:
            async_to_sync(channel_layer.group_send)(
                f'conversation_{conversation.id}',
                {
                    'type': 'user_presence',
                    'user_id': user.id,
                    'user_name': user.get_full_name(),
                    'status': 'online'
                }
            )
    
    @staticmethod
    def user_offline(user):
        """Mark user as offline and broadcast to relevant conversations"""
        
        # Get all conversations where user is a participant
        conversations = Conversation.objects.filter(participants=user)
        
        channel_layer = get_channel_layer()
        
        for conversation in conversations:
            async_to_sync(channel_layer.group_send)(
                f'conversation_{conversation.id}',
                {
                    'type': 'user_presence',
                    'user_id': user.id,
                    'user_name': user.get_full_name(),
                    'status': 'offline'
                }
            )