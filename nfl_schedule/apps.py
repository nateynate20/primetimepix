from django.apps import AppConfig


class NflScheduleConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'nfl_schedule'

def ready(self):
        # Import the CSV data when the app is ready
        from .views import import_nfl_schedule
        import_nfl_schedule(None)