# nfl_schedule/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('import_nfl_schedule/', views.import_nfl_schedule, name='import_nfl_schedule'),
    # Add other URL patterns for your nfl_schedule app as needed
]

