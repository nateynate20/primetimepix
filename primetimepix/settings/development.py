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

