import dj_database_url
import os
from .base import *

# SECURITY
DEBUG = False
ALLOWED_HOSTS = ['primetimepix.onrender.com']  # Replace with your domain

# Database
DATABASES = {
    'default': dj_database_url.config(
        default=os.getenv('DATABASE_URL'),
        conn_max_age=600,        # Persistent connections for performance
        ssl_require=True         # Ensure SSL if needed
    )
}

# Static files via WhiteNoise
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATIC_URL = '/static/'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
