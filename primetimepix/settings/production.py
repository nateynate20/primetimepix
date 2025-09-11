import dj_database_url
import os
from .base import *

# SECURITY
DEBUG = False
ALLOWED_HOSTS = ['primetimepix.onrender.com']

# Ensure DATABASE_URL exists
DATABASE_URL = os.getenv('DATABASE_URL')
if not DATABASE_URL:
    raise Exception("DATABASE_URL environment variable not set for production!")

# Database
DATABASES = {
    'default': dj_database_url.config(
        default=DATABASE_URL,
        conn_max_age=600,
        ssl_require=True
    )
}

# Static files via WhiteNoise
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATIC_URL = '/static/'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
