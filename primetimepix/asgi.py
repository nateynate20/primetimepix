# primetimepix/asgi.py
"""
ASGI config for primetimepix project.
"""
import os
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'primetimepix.settings')
application = get_asgi_application()