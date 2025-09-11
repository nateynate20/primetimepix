import os
import dj_database_url
from .base import *

DEBUG = False
ALLOWED_HOSTS = ['primetimepix.onrender.com']

# Postgres via DATABASE_URL
DATABASES = {
    'default': dj_database_url.config(
        default=os.getenv('DATABASE_URL'),
        conn_max_age=600,
        ssl_require=True
    )
}

# Ensure Whitenoise is used for static
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
