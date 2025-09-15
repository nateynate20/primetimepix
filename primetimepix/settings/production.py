import dj_database_url
import os
from .base import *

# SECURITY
DEBUG = False
ALLOWED_HOSTS = ['primetimepix.onrender.com']

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

# Email configuration for production with SendGrid
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = "smtp.sendgrid.net"
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = "apikey"  # This must be literally "apikey" for SendGrid
EMAIL_HOST_PASSWORD = os.getenv("SENDGRID_API_KEY", "")  # Your actual API key

# CRITICAL FIX: The FROM email must be a verified sender in SendGrid
# You need to verify this email address in SendGrid dashboard first!
DEFAULT_FROM_EMAIL = "evansna05@gmail.com"  # Change this to your verified sender
SERVER_EMAIL = DEFAULT_FROM_EMAIL

# Add this for debugging
if not EMAIL_HOST_PASSWORD:
    print("[WARNING] SENDGRID_API_KEY is not set!")
else:
    print(f"[SUCCESS] SendGrid configured with key starting with: {EMAIL_HOST_PASSWORD[:10]}...")

# Optional: For testing, you can temporarily use console backend
# EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"  # Uncomment for testing

EMAIL_DEBUG = True 
EMAIL_TIMEOUT = 10
# Security settings
SECURE_SSL_REDIRECT = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True

print(f"[PRODUCTION] Email configured: {bool(EMAIL_HOST_USER)}")

SITE_ID = 1