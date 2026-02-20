from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from .models import (
    Conversation, Message, Announcement, Notification,
    BroadcastList, MessageTemplate, EmailLog, SMSLog
)

class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    fields = ['sender', 'content_preview', 'created_at']
    readonly_fields = ['content_preview']
    
    def content_preview(self, obj):
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    content_preview.short_description = 'Content'

@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ['id', 'participants_list', 'message_count', 'last_message', 'updated_at']
    list_filter = ['updated_at']
    search_fields = ['participants__username']
    filter_horizontal = ['participants']
    inlines = [MessageInline]
    readonly_fields = ['created_at', 'updated_at']
    
    def participants_list(self, obj):
        return ", ".join([p.get_full_name() or p.username for p in obj.participants.all()[:3]])
    participants_list.short_description = 'Participants'
    
    def message_count(self, obj):
        return obj.messages.count()
    message_count.short_description = 'Messages'
    
    def last_message(self, obj):
        last = obj.get_last_message()
        if last:
            return f"{last.created_at.strftime('%Y-%m-%d %H:%M')}"
        return '-'

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['sender', 'conversation', 'content_preview', 'message_type', 'created_at']
    list_filter = ['message_type', 'created_at']
    search_fields = ['content', 'sender__username']
    date_hierarchy = 'created_at'
    filter_horizontal = ['read_by']
    readonly_fields = ['created_at', 'updated_at']
    
    def content_preview(self, obj):
        return obj.content[:75] + '...' if len(obj.content) > 75 else obj.content
    content_preview.short_description = 'Content'

@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ['title', 'audience_type', 'priority', 'publish_date', 'expiry_date', 'is_active']
    list_filter = ['audience_type', 'priority', 'publish_date']
    search_fields = ['title', 'content']
    date_hierarchy = 'publish_date'
    filter_horizontal = ['read_by']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Announcement Details', {
            'fields': ('title', 'content', 'priority')
        }),
        ('Audience', {
            'fields': ('audience_type', 'target_class_level', 'target_stream')
        }),
        ('Schedule', {
            'fields': ('publish_date', 'expiry_date')
        }),
        ('Attachments', {
            'fields': ('attachment',)
        }),
        ('Tracking', {
            'fields': ('read_by',),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def is_active(self, obj):
        return obj.is_active()
    is_active.boolean = True
    is_active.short_description = 'Active'

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['recipient', 'title', 'notification_type', 'is_read', 'created_at']
    list_filter = ['notification_type', 'is_read', 'created_at']
    search_fields = ['recipient__username', 'title', 'message']
    date_hierarchy = 'created_at'
    readonly_fields = ['created_at']
    
    actions = ['mark_as_read']
    
    def mark_as_read(self, request, queryset):
        queryset.update(is_read=True, read_at=timezone.now())
    mark_as_read.short_description = "Mark selected notifications as read"

@admin.register(BroadcastList)
class BroadcastListAdmin(admin.ModelAdmin):
    list_display = ['name', 'member_count', 'filter_by_role', 'filter_by_class', 'created_at']
    list_filter = ['filter_by_role', 'created_at']
    search_fields = ['name', 'description']
    filter_horizontal = ['members']
    readonly_fields = ['created_at', 'updated_at']
    
    def member_count(self, obj):
        return obj.members.count()
    member_count.short_description = 'Members'
    
    actions = ['update_members']
    
    def update_members(self, request, queryset):
        for broadcast_list in queryset:
            broadcast_list.update_members()
        self.message_user(request, f"Updated {queryset.count()} broadcast lists.")
    update_members.short_description = "Update members from filters"

@admin.register(MessageTemplate)
class MessageTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'template_type', 'subject_preview', 'created_by', 'updated_at']
    list_filter = ['template_type', 'created_at']
    search_fields = ['name', 'subject', 'content']
    readonly_fields = ['created_at', 'updated_at']
    
    def subject_preview(self, obj):
        return obj.subject[:50] + '...' if len(obj.subject) > 50 else obj.subject
    subject_preview.short_description = 'Subject'

@admin.register(EmailLog)
class EmailLogAdmin(admin.ModelAdmin):
    list_display = ['recipient', 'subject', 'status', 'sent_at']
    list_filter = ['status', 'sent_at']
    search_fields = ['recipient', 'subject']
    date_hierarchy = 'sent_at'
    readonly_fields = ['sent_at']

@admin.register(SMSLog)
class SMSLogAdmin(admin.ModelAdmin):
    list_display = ['recipient', 'message_preview', 'status', 'sent_at']
    list_filter = ['status', 'sent_at']
    search_fields = ['recipient', 'message']
    date_hierarchy = 'sent_at'
    readonly_fields = ['sent_at']
    
    def message_preview(self, obj):
        return obj.message[:50] + '...' if len(obj.message) > 50 else obj.message
    message_preview.short_description = 'Message'