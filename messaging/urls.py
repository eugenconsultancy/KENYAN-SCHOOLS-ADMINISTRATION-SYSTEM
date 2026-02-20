from django.urls import path
from . import views

app_name = 'messaging'

urlpatterns = [
    # Inbox
    path('', views.inbox, name='inbox'),
    path('compose/', views.compose_message, name='compose'),
    path('conversation/<int:conversation_id>/', views.conversation_detail, name='conversation'),
    
    # Announcements
    path('announcements/', views.announcement_list, name='announcement_list'),
    path('announcements/create/', views.announcement_create, name='announcement_create'),
    path('announcements/<int:announcement_id>/', views.announcement_detail, name='announcement_detail'),
    path('announcements/<int:announcement_id>/edit/', views.announcement_edit, name='announcement_edit'),
    path('announcements/<int:announcement_id>/delete/', views.announcement_delete, name='announcement_delete'),
    
    # Notifications
    path('notifications/', views.notifications, name='notifications'),
    path('notifications/<int:notification_id>/', views.notification_detail, name='notification_detail'),
    path('notifications/<int:notification_id>/mark-read/', views.mark_notification_read, name='mark_notification_read'),
    path('notifications/mark-all-read/', views.mark_all_read, name='mark_all_read'),
    
    # Broadcast Lists
    path('broadcast-lists/', views.broadcast_list_list, name='broadcast_list_list'),
    path('broadcast-lists/create/', views.broadcast_list_create, name='broadcast_list_create'),
    path('broadcast-lists/<int:list_id>/edit/', views.broadcast_list_edit, name='broadcast_list_edit'),
    path('broadcast-lists/<int:list_id>/delete/', views.broadcast_list_delete, name='broadcast_list_delete'),
    path('broadcast-lists/<int:list_id>/members/', views.broadcast_list_members, name='broadcast_list_members'),
    
    # Templates
    path('templates/', views.template_list, name='template_list'),
    path('templates/create/', views.template_create, name='template_create'),
    path('templates/<int:template_id>/edit/', views.template_edit, name='template_edit'),
    path('templates/<int:template_id>/delete/', views.template_delete, name='template_delete'),
    path('templates/<int:template_id>/preview/', views.template_preview, name='template_preview'),
    
    # Settings
    path('settings/', views.notification_settings, name='notification_settings'),
    
    # API endpoints
    path('api/unread-count/', views.get_unread_count, name='api_unread_count'),
    path('api/search-users/', views.search_users, name='api_search_users'),
]