import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from asgiref.sync import async_to_sync
from django.contrib.auth import get_user_model

User = get_user_model()

class NotificationConsumer(AsyncWebsocketConsumer):
    """Consumer for real-time notifications"""
    
    async def connect(self):
        self.user = self.scope['user']
        
        if not self.user.is_authenticated:
            await self.close()
        else:
            # Create a unique group for this user
            self.notification_group_name = f'user_{self.user.id}_notifications'
            self.conversations_group_name = f'user_{self.user.id}_conversations'
            
            # Join groups
            await self.channel_layer.group_add(
                self.notification_group_name,
                self.channel_name
            )
            await self.channel_layer.group_add(
                self.conversations_group_name,
                self.channel_name
            )
            
            await self.accept()
            
            # Send unread count on connect
            await self.send_unread_count()
    
    async def disconnect(self, close_code):
        # Leave groups
        if hasattr(self, 'notification_group_name'):
            await self.channel_layer.group_discard(
                self.notification_group_name,
                self.channel_name
            )
        if hasattr(self, 'conversations_group_name'):
            await self.channel_layer.group_discard(
                self.conversations_group_name,
                self.channel_name
            )
    
    async def receive(self, text_data):
        """Handle messages from WebSocket"""
        data = json.loads(text_data)
        message_type = data.get('type')
        
        if message_type == 'mark_read':
            await self.mark_notification_read(data.get('notification_id'))
        elif message_type == 'typing':
            await self.handle_typing(data)
    
    async def notification_message(self, event):
        """Send notification to WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'notification',
            'notification': event['notification']
        }))
        
        # Also send updated unread count
        await self.send_unread_count()
    
    async def conversation_message(self, event):
        """Send new message to WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'new_message',
            'message': event['message'],
            'conversation_id': event['conversation_id'],
            'sender': event['sender'],
            'timestamp': event['timestamp']
        }))
    
    async def conversation_updated(self, event):
        """Notify that conversation list should be refreshed"""
        await self.send(text_data=json.dumps({
            'type': 'conversation_updated',
            'conversation_id': event['conversation_id']
        }))
    
    async def typing_indicator(self, event):
        """Send typing indicator"""
        await self.send(text_data=json.dumps({
            'type': 'typing',
            'conversation_id': event['conversation_id'],
            'user': event['user'],
            'is_typing': event['is_typing']
        }))
    
    async def send_unread_count(self):
        """Send unread count to client"""
        unread_count = await self.get_unread_count()
        await self.send(text_data=json.dumps({
            'type': 'unread_count',
            'count': unread_count
        }))
    
    @database_sync_to_async
    def get_unread_count(self):
        """Get unread notifications count"""
        from .models import Notification
        return Notification.objects.filter(
            recipient=self.user,
            is_read=False
        ).count()
    
    @database_sync_to_async
    def mark_notification_read(self, notification_id):
        """Mark notification as read"""
        from .models import Notification
        try:
            notification = Notification.objects.get(
                id=notification_id,
                recipient=self.user
            )
            notification.mark_as_read()
            return True
        except Notification.DoesNotExist:
            return False
    
    async def handle_typing(self, data):
        """Handle typing indicator"""
        conversation_id = data.get('conversation_id')
        is_typing = data.get('is_typing', True)
        
        # Broadcast to other participants
        await self.channel_layer.group_send(
            f'conversation_{conversation_id}',
            {
                'type': 'typing_indicator',
                'conversation_id': conversation_id,
                'user': self.user.get_full_name(),
                'is_typing': is_typing
            }
        )


class ChatConsumer(AsyncWebsocketConsumer):
    """Consumer for real-time chat in a specific conversation"""
    
    async def connect(self):
        self.user = self.scope['user']
        self.conversation_id = self.scope['url_route']['kwargs']['conversation_id']
        self.conversation_group_name = f'conversation_{self.conversation_id}'
        
        if not self.user.is_authenticated:
            await self.close()
        else:
            # Check if user is participant
            if await self.is_participant():
                # Join conversation group
                await self.channel_layer.group_add(
                    self.conversation_group_name,
                    self.channel_name
                )
                await self.accept()
                
                # Mark messages as read
                await self.mark_messages_read()
            else:
                await self.close()
    
    async def disconnect(self, close_code):
        # Leave conversation group
        await self.channel_layer.group_discard(
            self.conversation_group_name,
            self.channel_name
        )
    
    async def receive(self, text_data):
        """Handle incoming WebSocket messages"""
        data = json.loads(text_data)
        message_type = data.get('type')
        
        if message_type == 'new_message':
            await self.save_and_broadcast_message(data)
        elif message_type == 'mark_read':
            await self.mark_messages_read()
    
    async def save_and_broadcast_message(self, data):
        """Save message and broadcast to group"""
        content = data.get('content')
        
        # Save message to database
        message = await self.save_message(content)
        
        if message:
            # Broadcast to conversation group
            await self.channel_layer.group_send(
                self.conversation_group_name,
                {
                    'type': 'chat_message',
                    'message': {
                        'id': message.id,
                        'content': message.content,
                        'sender': self.user.get_full_name(),
                        'sender_id': self.user.id,
                        'timestamp': message.created_at.isoformat(),
                        'attachment': message.attachment.url if message.attachment else None
                    }
                }
            )
            
            # Notify other participants about new message
            await self.notify_participants(message)
    
    async def chat_message(self, event):
        """Send message to WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'new_message',
            'message': event['message']
        }))
    
    @database_sync_to_async
    def is_participant(self):
        """Check if user is participant in conversation"""
        from .models import Conversation
        try:
            conversation = Conversation.objects.get(id=self.conversation_id)
            return conversation.participants.filter(id=self.user.id).exists()
        except Conversation.DoesNotExist:
            return False
    
    @database_sync_to_async
    def save_message(self, content):
        """Save message to database"""
        from .models import Conversation, Message
        try:
            conversation = Conversation.objects.get(id=self.conversation_id)
            message = Message.objects.create(
                conversation=conversation,
                sender=self.user,
                content=content
            )
            return message
        except Exception:
            return None
    
    @database_sync_to_async
    def mark_messages_read(self):
        """Mark all messages in conversation as read"""
        from .models import Message
        Message.objects.filter(
            conversation_id=self.conversation_id
        ).exclude(
            sender=self.user
        ).exclude(
            read_by=self.user
        ).update(read_by=self.user)
    
    @database_sync_to_async
    def notify_participants(self, message):
        """Notify other participants about new message"""
        from channels.layers import get_channel_layer
        from .models import Conversation
        
        channel_layer = get_channel_layer()
        conversation = Conversation.objects.get(id=self.conversation_id)
        participants = conversation.participants.exclude(id=self.user.id)
        
        for participant in participants:
            async_to_sync(channel_layer.group_send)(
                f'user_{participant.id}_conversations',
                {
                    'type': 'conversation_message',
                    'message': {
                        'id': message.id,
                        'content': message.content[:50],
                        'sender': self.user.get_full_name(),
                        'conversation_id': conversation.id,
                        'timestamp': message.created_at.isoformat()
                    },
                    'conversation_id': conversation.id,
                    'sender': self.user.get_full_name(),
                    'timestamp': message.created_at.isoformat()
                }
            )