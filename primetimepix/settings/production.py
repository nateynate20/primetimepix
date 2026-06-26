import dj_database_url
import os
from .base import *

# SECURITY
DEBUG = False
ALLOWED_HOSTS = [
    '.up.railway.app',
    '.railway.app',
    'primetimepixsports.com',
    'www.primetimepixsports.com',
]

CSRF_TRUSTED_ORIGINS = [
    'https://*.up.railway.app',
    'https://*.railway.app',
    'https://primetimepixsports.com',
    'https://www.primetimepixsports.com',
]

# Database
DATABASE_URL = os.getenv('DATABASE_URL')
if not DATABASE_URL:
    raise Exception("DATABASE_URL environment variable not set for production!")

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

# Email via Brevo HTTP API (SMTP ports blocked on Railway)
EMAIL_BACKEND = "anymail.backends.brevo.EmailBackend"
ANYMAIL = {
    "BREVO_API_KEY": os.getenv("BREVO_API_KEY", ""),
}
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "picks@primetimepixsports.com")
SERVER_EMAIL = DEFAULT_FROM_EMAIL

if not ANYMAIL["BREVO_API_KEY"]:
    print("[WARNING] BREVO_API_KEY is not set! Emails will not send.")
# Security settings - Railway handles SSL at the proxy level
SECURE_SSL_REDIRECT = False  # Railway's proxy handles HTTPS
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True


SITE_ID = 1