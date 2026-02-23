"""
Django settings for config project.
Enhanced with Jazzmin (AdminLTE 3) for a beautiful admin interface.
Production-ready configuration for Railway deployment.
"""

from pathlib import Path
import os
import sys
from decouple import config
import dj_database_url  # For Railway database URL parsing

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config('SECRET_KEY', default='django-insecure-your-secret-key-here-change-in-production')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config('DEBUG', default=False, cast=bool)  # Default to False for production

# Railway provides the PORT environment variable
PORT = config('PORT', default='8000')

# ALLOWED_HOSTS configuration for Railway
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1,.up.railway.app').split(',')

# CSRF Trusted Origins for Railway
CSRF_TRUSTED_ORIGINS = config('CSRF_TRUSTED_ORIGINS', 
                              default='http://localhost:8000,http://127.0.0.1:8000,https://*.up.railway.app').split(',')

# Application definition
INSTALLED_APPS = [
    # Jazzmin MUST come before django.contrib.admin
    'jazzmin',  # AdminLTE 3 theme for admin
    
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Third party apps
    'channels',  # For WebSocket support
    'rest_framework',
    'crispy_forms',
    'crispy_tailwind',
    'django_htmx',
    
    # Local apps
    'accounts',
    'students',
    'teachers',
    'academics',
    'finance',
    'attendance',
    'messaging',
    'dashboard',
    'reports',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # Must be after SecurityMiddleware
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django_htmx.middleware.HtmxMiddleware',
    'accounts.middleware.RoleBasedAccessMiddleware',
    'accounts.middleware.AuditLogMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'accounts.context_processors.site_settings',
                'accounts.context_processors.notification_count',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'  # For Channels

# Database configuration for Railway - Uses DATABASE_URL from environment
DATABASES = {
    'default': dj_database_url.config(
        default='sqlite:///' + str(BASE_DIR / 'db.sqlite3'),
        conn_max_age=600,
        conn_health_checks=True,
    )
}

# Custom user model
AUTH_USER_MODEL = 'accounts.User'

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Africa/Nairobi'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Crispy forms
CRISPY_ALLOWED_TEMPLATE_PACKS = "tailwind"
CRISPY_TEMPLATE_PACK = "tailwind"

# Login URLs
LOGIN_URL = 'accounts:login'
LOGIN_REDIRECT_URL = 'dashboard:home'
LOGOUT_REDIRECT_URL = 'accounts:login'

# Session settings
SESSION_COOKIE_AGE = 3600  # 1 hour
SESSION_SAVE_EVERY_REQUEST = True
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

# Security settings - automatically enabled in production (when DEBUG=False)
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Email configuration
EMAIL_BACKEND = config('EMAIL_BACKEND', default='django.core.mail.backends.console.EmailBackend')
EMAIL_HOST = config('EMAIL_HOST', default='')
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='webmaster@localhost')

# REST Framework settings
REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
    ],
}

# Kenyan schools specific settings
TERMS = [
    (1, 'Term 1'),
    (2, 'Term 2'),
    (3, 'Term 3'),
]

CLASS_LEVELS = [
    (1, 'Form 1'),
    (2, 'Form 2'),
    (3, 'Form 3'),
    (4, 'Form 4'),
]

STREAMS = [
    ('East', 'East'),
    ('West', 'West'),
    ('North', 'North'),
    ('South', 'South'),
]

GENDER_CHOICES = [
    ('M', 'Male'),
    ('F', 'Female'),
]

# =============================================================================
# JAZZMIN ADMIN THEME CONFIGURATION (AdminLTE 3)
# =============================================================================

JAZZMIN_SETTINGS = {
    "site_title": "Kenyan Schools System Admin",
    "site_header": "Kenyan Schools System",
    "site_brand": "KSS Admin",
    "site_logo": "images/logo.png",
    "site_logo_classes": "img-circle",
    "welcome_sign": "Welcome to the Kenyan Schools System Administration",
    "copyright": "Kenyan Schools System Ltd",
    "search_model": ["accounts.User", "students.Student", "teachers.Teacher"],
    "user_avatar": None,
    
    "topmenu_links": [
        {"name": "Home", "url": "admin:index", "permissions": ["auth.view_user"]},
        {"name": "Support", "url": "https://github.com/eugenconsultancy/KENYAN-SCHOOLS-ADMINISTRATION-SYSTEM/issues", "new_window": True},
        {"model": "auth.User"},
        {"app": "accounts"},
    ],
    
    "usermenu_links": [
        {"name": "Support", "url": "https://github.com/eugenconsultancy/KENYAN-SCHOOLS-ADMINISTRATION-SYSTEM/issues", "new_window": True},
        {"model": "auth.user"}
    ],
    
    "show_sidebar": True,
    "navigation_expanded": True,
    "hide_apps": [],
    "hide_models": [],
    "order_with_respect_to": ["accounts", "students", "teachers", "academics", "finance", "attendance", "messaging"],
    
    "custom_links": {
        "accounts": [{
            "name": "Audit Logs",
            "url": "accounts:audit_logs",
            "icon": "fas fa-history",
            "permissions": ["accounts.view_auditlog"]
        }]
    },
    
    "icons": {
        "accounts": "fas fa-users-cog",
        "accounts.User": "fas fa-user",
        "accounts.Group": "fas fa-users",
        "accounts.Notification": "fas fa-bell",
        "accounts.AuditLog": "fas fa-history",
        "accounts.LoginLog": "fas fa-sign-in-alt",
        
        "students": "fas fa-user-graduate",
        "students.Student": "fas fa-user-graduate",
        "students.Parent": "fas fa-user-friends",
        "students.Club": "fas fa-futbol",
        "students.Sport": "fas fa-running",
        "students.StudentDocument": "fas fa-file-alt",
        "students.StudentNote": "fas fa-sticky-note",
        
        "teachers": "fas fa-chalkboard-teacher",
        "teachers.Teacher": "fas fa-chalkboard-teacher",
        "teachers.TeacherAttendance": "fas fa-calendar-check",
        "teachers.TeacherLeave": "fas fa-umbrella-beach",
        "teachers.TeacherDocument": "fas fa-file-pdf",
        "teachers.TeacherPerformance": "fas fa-star",
        "teachers.TeacherSalary": "fas fa-money-bill-wave",
        
        "academics": "fas fa-book-open",
        "academics.AcademicYear": "fas fa-calendar-alt",
        "academics.Term": "fas fa-calendar-week",
        "academics.Class": "fas fa-school",
        "academics.Subject": "fas fa-book",
        "academics.Exam": "fas fa-file-alt",
        "academics.Result": "fas fa-chart-line",
        "academics.Homework": "fas fa-home",
        
        "finance": "fas fa-coins",
        "finance.FeeStructure": "fas fa-tags",
        "finance.Invoice": "fas fa-file-invoice",
        "finance.Payment": "fas fa-money-bill-wave",
        "finance.Expense": "fas fa-receipt",
        "finance.Budget": "fas fa-chart-pie",
        
        "attendance": "fas fa-clock",
        "attendance.Attendance": "fas fa-calendar-check",
        "attendance.TeacherAttendance": "fas fa-user-clock",
        "attendance.Holiday": "fas fa-umbrella-beach",
        
        "messaging": "fas fa-envelope",
        "messaging.Conversation": "fas fa-comments",
        "messaging.Message": "fas fa-comment",
        "messaging.Announcement": "fas fa-bullhorn",
        "messaging.Notification": "fas fa-bell",
        "messaging.BroadcastList": "fas fa-list",
        "messaging.MessageTemplate": "fas fa-file-alt",
    },
    
    "default_icon_parents": "fas fa-chevron-circle-right",
    "default_icon_children": "fas fa-circle",
    "related_modal_active": True,
    "custom_css": None,
    "custom_js": None,
    "use_google_fonts_cdn": True,
    "show_ui_builder": False,
    "changeform_format": "horizontal_tabs",
    "changeform_format_overrides": {
        "accounts.user": "collapsible",
        "auth.group": "vertical_tabs",
    },
}

JAZZMIN_UI_TWEAKS = {
    "navbar_small_text": False,
    "footer_small_text": False,
    "body_small_text": False,
    "brand_small_text": False,
    "brand_colour": False,
    "accent": "accent-primary",
    "navbar": "navbar-dark",
    "no_navbar_border": False,
    "navbar_fixed": True,
    "layout_boxed": False,
    "footer_fixed": False,
    "sidebar_fixed": True,
    "sidebar": "sidebar-dark-primary",
    "sidebar_nav_small_text": False,
    "sidebar_disable_expand": False,
    "sidebar_nav_child_indent": True,
    "sidebar_nav_compact_style": False,
    "sidebar_nav_legacy_style": False,
    "sidebar_nav_flat_style": False,
    "theme": "default",
    "dark_mode_theme": None,
    "button_classes": {
        "primary": "btn-primary",
        "secondary": "btn-secondary",
        "info": "btn-info",
        "warning": "btn-warning",
        "danger": "btn-danger",
        "success": "btn-success",
    },
}

# =============================================================================
# CHANNELS AND WEBSOCKET CONFIGURATION
# =============================================================================

# Channel layers for WebSocket communication
# Uses Redis from Railway environment variable
REDIS_URL = config('REDIS_URL', default=None)

if REDIS_URL:
    CHANNEL_LAYERS = {
        'default': {
            'BACKEND': 'channels_redis.core.RedisChannelLayer',
            'CONFIG': {
                "hosts": [REDIS_URL],
                "capacity": 1500,
                "expiry": 60,
            },
        },
    }
else:
    # Fallback to in-memory channel layer for development
    CHANNEL_LAYERS = {
        'default': {
            'BACKEND': 'channels.layers.InMemoryChannelLayer',
        },
    }

# WebSocket specific settings
WEBSOCKET_TIMEOUT = 60
WEBSOCKET_MAX_SIZE = 1024 * 1024  # 1MB

# =============================================================================
# CACHE CONFIGURATION
# =============================================================================

if REDIS_URL:
    CACHES = {
        'default': {
            'BACKEND': 'django_redis.cache.RedisCache',
            'LOCATION': REDIS_URL,
            'OPTIONS': {
                'CLIENT_CLASS': 'django_redis.client.DefaultClient',
                'CONNECTION_POOL_CLASS': 'redis.BlockingConnectionPool',
                'CONNECTION_POOL_CLASS_KWARGS': {
                    'max_connections': 50,
                    'timeout': 20,
                },
                'MAX_CONNECTIONS': 1000,
                'PICKLE_VERSION': -1,
            },
            'KEY_PREFIX': 'kss',
        }
    }
else:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'kss-cache',
            'KEY_PREFIX': 'kss',
        }
    }

# Optional: Use Redis for session storage
# SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
# SESSION_CACHE_ALIAS = 'default'

# =============================================================================
# NOTIFICATION SETTINGS
# =============================================================================

NOTIFICATION_SETTINGS = {
    'PAGE_SIZE': 20,
    'MAX_TITLE_LENGTH': 200,
    'MAX_MESSAGE_LENGTH': 500,
    'CLEANUP_DAYS': 30,
}

# =============================================================================
# MESSAGING SETTINGS
# =============================================================================

MESSAGING_SETTINGS = {
    'MAX_ATTACHMENT_SIZE': 10 * 1024 * 1024,  # 10MB
    'ALLOWED_ATTACHMENT_TYPES': [
        'image/jpeg',
        'image/png',
        'image/gif',
        'application/pdf',
        'application/msword',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'text/plain',
    ],
    'MAX_MESSAGE_LENGTH': 5000,
    'TYPING_TIMEOUT': 3,
    'MESSAGE_PAGE_SIZE': 50,
}

# =============================================================================
# REAL-TIME FEATURES SETTINGS
# =============================================================================

REALTIME_SETTINGS = {
    'ENABLE_TYPING_INDICATORS': True,
    'ENABLE_READ_RECEIPTS': True,
    'ENABLE_PRESENCE': True,
    'PRESENCE_TIMEOUT': 60,
    'RECONNECT_DELAY': 3,
}

# =============================================================================
# LOGGING CONFIGURATION
# =============================================================================

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
        'file': {
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'django.log',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
        },
        'channels': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
        },
    },
}

# Create logs directory if it doesn't exist
LOGS_DIR = BASE_DIR / 'logs'
if not os.path.exists(LOGS_DIR):
    os.makedirs(LOGS_DIR)

# =============================================================================
# CORS SETTINGS
# =============================================================================

CORS_ALLOWED_ORIGINS = [
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]

# Add Railway domain to CORS if in production
if not DEBUG:
    CORS_ALLOWED_ORIGINS.append("https://*.up.railway.app")

CORS_ALLOW_CREDENTIALS = True

# =============================================================================
# SECURITY HEADERS
# =============================================================================

SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# =============================================================================
# SESSION SECURITY
# =============================================================================

SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = 'Lax'

# =============================================================================
# FILE UPLOAD SETTINGS
# =============================================================================

FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB
DATA_UPLOAD_MAX_NUMBER_FIELDS = 1000

# =============================================================================
# RAILWAY SPECIFIC SETTINGS
# =============================================================================

# Check if running on Railway (presence of RAILWAY_ENVIRONMENT variable)
IS_RAILWAY = config('RAILWAY_ENVIRONMENT', default=None) is not None

if IS_RAILWAY:
    # Ensure static files are collected
    STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
    
    # Use Railway's Redis for channels
    if REDIS_URL:
        CHANNEL_LAYERS = {
            'default': {
                'BACKEND': 'channels_redis.core.RedisChannelLayer',
                'CONFIG': {
                    "hosts": [REDIS_URL],
                    "capacity": 1500,
                    "expiry": 60,
                },
            },
        }

# =============================================================================
# SILENCED SYSTEM CHECKS
# =============================================================================

SILENCED_SYSTEM_CHECKS = [
    'security.W003',  # Silence CSRF check warning for development
]