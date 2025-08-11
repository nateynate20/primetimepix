#apps/picks/apps.py
from django.apps import AppConfig

class PicksConfig(AppConfig):  # I suggest renaming to PicksConfig for clarity
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.picks'
