# primetimepix/wsgi.py
"""
WSGI config for primetimepix project.
"""
import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'primetimepix.settings')
application = get_wsgi_application()