# apps/leagues/apps.py
from django.apps import AppConfig

class LeaguesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.leagues'

    def ready(self):
        import apps.leagues.signals
