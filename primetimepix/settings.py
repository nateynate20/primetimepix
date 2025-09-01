# primetimepix/settings.py
import os
<<<<<<< HEAD
from pathlib import Path
=======
from pathlib import Path
from decouple import config, Csv
import dj_database_url
>>>>>>> 80abcf7c5cfbf6c12ebf84c535599e472ccfb913

<<<<<<< HEAD
# Base directory
BASE_DIR = Path(__file__).resolve().parent.parent
=======
BASE_DIR = Path(__file__).resolve().parent.parent
>>>>>>> 80abcf7c5cfbf6c12ebf84c535599e472ccfb913

<<<<<<< HEAD
# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'your-secret-key-here'  # Replace before deploying

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = []  # Add your domain in production
=======
SECRET_KEY = config('SECRET_KEY', default='super-secret-dev-key')
THESPORTSDB_API_KEY = config('THESPORTSDB_API_KEY', default='123')
>>>>>>> 80abcf7c5cfbf6c12ebf84c535599e472ccfb913

<<<<<<< HEAD

=======
DEBUG = config('DEBUG', cast=bool, default=True)

ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1').split(',')


>>>>>>> 80abcf7c5cfbf6c12ebf84c535599e472ccfb913
# Application definition
INSTALLED_APPS = [
    'grappelli',
<<<<<<< HEAD
=======
    'import_export',
>>>>>>> 80abcf7c5cfbf6c12ebf84c535599e472ccfb913

    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

<<<<<<< HEAD
    # Local apps
=======
    # Your apps
    'primetimepix.apps.PrimetimepixConfig',
>>>>>>> 80abcf7c5cfbf6c12ebf84c535599e472ccfb913
    'apps.games',
    'apps.leagues',
    'apps.picks',
    'apps.users',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # for static files on Render
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'primetimepix.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
<<<<<<< HEAD
        'DIRS': [BASE_DIR / 'templates'],  # Use this for global templates
=======
        'DIRS': [os.path.join(BASE_DIR, 'templates')],  # optional shared template dir
>>>>>>> 80abcf7c5cfbf6c12ebf84c535599e472ccfb913
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
<<<<<<< HEAD
                'django.template.context_processors.request',  # Required for admin & auth
=======
                'django.template.context_processors.request',
>>>>>>> 80abcf7c5cfbf6c12ebf84c535599e472ccfb913
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
<<<<<<< HEAD
=======

               'apps.games.context_processors.live_scores_ticker',
               'apps.picks.context_processors.user_leagues',

>>>>>>> 80abcf7c5cfbf6c12ebf84c535599e472ccfb913
            ],
        },
    },
]

WSGI_APPLICATION = 'primetimepix.wsgi.application'


<<<<<<< HEAD
# Database
=======
# Database setup for local + Render
>>>>>>> 80abcf7c5cfbf6c12ebf84c535599e472ccfb913
DATABASES = {
<<<<<<< HEAD
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',  # Or PostgreSQL if you're using that
        'NAME': BASE_DIR / 'db.sqlite3',
    }
=======
    'default': dj_database_url.config(
        default=f"sqlite:///{os.path.join(BASE_DIR, 'db.sqlite3')}", conn_max_age=600
    )
>>>>>>> 80abcf7c5cfbf6c12ebf84c535599e472ccfb913
}

<<<<<<< HEAD

# Password validation
=======
# Password validation
>>>>>>> 80abcf7c5cfbf6c12ebf84c535599e472ccfb913
AUTH_PASSWORD_VALIDATORS = [
<<<<<<< HEAD
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
=======
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
>>>>>>> 80abcf7c5cfbf6c12ebf84c535599e472ccfb913
]

<<<<<<< HEAD

# Internationalization
=======
# Time settings
>>>>>>> 80abcf7c5cfbf6c12ebf84c535599e472ccfb913
LANGUAGE_CODE = 'en-us'
<<<<<<< HEAD
TIME_ZONE = 'UTC'
=======
TIME_ZONE = 'America/New_York'
>>>>>>> 80abcf7c5cfbf6c12ebf84c535599e472ccfb913
USE_I18N = True
<<<<<<< HEAD
USE_L10N = True
=======
>>>>>>> 80abcf7c5cfbf6c12ebf84c535599e472ccfb913
USE_TZ = True

<<<<<<< HEAD

# Static files (CSS, JavaScript, Images)
=======
# Static + Media settings
>>>>>>> 80abcf7c5cfbf6c12ebf84c535599e472ccfb913
STATIC_URL = '/static/'
<<<<<<< HEAD
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'
=======
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'primetimepix/static')]
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
>>>>>>> 80abcf7c5cfbf6c12ebf84c535599e472ccfb913

<<<<<<< HEAD
# Media files (uploads, profile images, etc.)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
=======
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
>>>>>>> 80abcf7c5cfbf6c12ebf84c535599e472ccfb913

<<<<<<< HEAD
# Login & Redirect Settings
LOGIN_REDIRECT_URL = 'dashboard'
=======
# Auth
LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'landing_page'
>>>>>>> 80abcf7c5cfbf6c12ebf84c535599e472ccfb913
LOGOUT_REDIRECT_URL = 'landing_page'
LOGIN_URL = 'login_user'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
