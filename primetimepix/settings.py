# primetimepix/settings.py
from pathlib import Path
import os
from django.contrib.messages import constants as messages
from decouple import config
import dj_database_url

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config('SECRET_KEY', default='your-secret-key-here')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config('DEBUG', default=True, cast=bool)

ALLOWED_HOSTS = ['localhost', '127.0.0.1']


# Application definition
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


# NFL Data Settings
NFL_CURRENT_SEASON = 2023
NFL_PRIMETIME_HOURS = [17, 20]  # 5 PM and 8 PM starts
NFL_DATA_CACHE_TIMEOUT = 3600  # 1 hour cache for NFL data


# Cache settings for NFL data
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}


# Timezone settings (important for game times)
TIME_ZONE = 'America/New_York'
USE_TZ = True


# Static + Media settings
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'primetimepix/static']
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')


# Auth
LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'landing_page'
LOGOUT_REDIRECT_URL = 'landing_page'
LOGIN_URL = 'login_user'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

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
                'apps.games.context_processors.live_scores_ticker',
                'apps.picks.context_processors.user_leagues',
            ],
        },
    },
]

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',  # Use SQLite as the database engine
        'NAME': BASE_DIR / 'db.sqlite3',  # Path to the SQLite database file
    }
}

ROOT_URLCONF = 'primetimepix.urls'
