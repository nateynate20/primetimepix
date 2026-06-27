from .base import *

DEBUG = True

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']

SECRET_KEY = 'test-secret-key-not-for-production'

STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'
