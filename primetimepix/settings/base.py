from pathlib import Path
import os
from django.contrib.messages import constants as messages
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# --------------------------
# Paths
# --------------------------
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# --------------------------
# Security
# --------------------------
SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-dev-key-change-in-production')
DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 'localhost').split(',')

# --------------------------
# Installed Apps
# --------------------------
INSTALLED_APPS = [
    'grappelli',
    'import_export',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'primetimepix.apps.PrimetimepixConfig',
    'apps.games.apps.GamesConfig',
    'apps.users.apps.UsersConfig',
    'apps.leagues.apps.LeaguesConfig',
    'apps.picks.apps.PicksConfig',
]

# --------------------------
# Middleware
# --------------------------
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'primetimepix.urls'

# --------------------------
# Templates
# --------------------------
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'primetimepix' / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'apps.picks.context_processors.user_leagues',
            ],
        },
    },
]

WSGI_APPLICATION = 'primetimepix.wsgi.application'

# --------------------------
# Auth / Password Validators
# --------------------------
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# --------------------------
# Internationalization
# --------------------------
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'US/Eastern'
USE_I18N = True
USE_TZ = True

# --------------------------
# Static Files
# --------------------------
STATIC_URL = '/static/'
STATICFILES_DIRS = [
    BASE_DIR / 'primetimepix' / 'static',  # your app static files
]
STATIC_ROOT = BASE_DIR / 'staticfiles'  # collectstatic destination

# --------------------------
# Media Files
# --------------------------
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# --------------------------
# Default Primary Key Field Type
# --------------------------
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# --------------------------
# Login / Logout
# --------------------------
LOGIN_URL = '/users/login_user/'
LOGIN_REDIRECT_URL = '/users/dashboard/'
LOGOUT_REDIRECT_URL = '/'

# --------------------------
# Messages
# --------------------------
MESSAGE_TAGS = {
    messages.DEBUG: 'secondary',
    messages.INFO: 'info',
    messages.SUCCESS: 'success',
    messages.WARNING: 'warning',
    messages.ERROR: 'danger',
}

# --------------------------
# Email Configuration
# --------------------------
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.getenv('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', 587))
EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'True').lower() == 'true'
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', 'noreply@primetimepix.com')
SERVER_EMAIL = DEFAULT_FROM_EMAIL

# --------------------------
# Site Info
# --------------------------
SITE_URL = os.getenv('SITE_URL', 'http://localhost:8000')
SITE_NAME = 'PrimeTimePix'

# --------------------------
# Logging
# --------------------------
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {'format': '{levelname} {asctime} {module} {message}', 'style': '{'},
    },
    'handlers': {
        'console': {'class': 'logging.StreamHandler', 'formatter': 'verbose'},
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': os.getenv('DJANGO_LOG_LEVEL', 'INFO'),
            'propagate': False,
        },
    },
}
