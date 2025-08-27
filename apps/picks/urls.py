#apps/picks/urls.py
from django.urls import path
from .views import display_nfl_schedule, standings, general_standings

urlpatterns = [
    path('schedule/', display_nfl_schedule, name='schedule'),
    path('standings/', standings, name='standings'),
    path('general-standings/', general_standings, name='general_standings'),
]
