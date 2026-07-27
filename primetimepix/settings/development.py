from .base import *

#SECRET_KEY=to8@3b&6aowdu*d5l)t6!#n&e+cv10pvv&bzr!j4h)0yp0^^3_
DEBUG = True
ALLOWED_HOSTS = ['localhost', '127.0.0.1']

# Use local SQLite
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Include static files from app directories
STATICFILES_DIRS = [BASE_DIR / 'primetimepix' / 'static']

# Print emails to the console instead of hitting a real SMTP server.
# Without this, base.py's SMTP backend makes signup (which sends a welcome
# email) block on an outbound connection locally, hanging the request.
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

