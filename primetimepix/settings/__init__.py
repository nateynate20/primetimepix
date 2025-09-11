import os
from dotenv import load_dotenv

load_dotenv()

# Determine which settings to use
environment = os.getenv('DJANGO_SETTINGS_MODULE', 'primetimepix.settings.development')

if 'production' in environment:
    from .production import *
elif 'staging' in environment:
    from .staging import *
else:
    from .development import *