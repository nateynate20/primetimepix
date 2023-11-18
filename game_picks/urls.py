#game_picks/urls.py
from django.urls import path
from .views import display_nfl_schedule
from .views import standings 

urlpatterns = [
    path('schedule/', display_nfl_schedule, name='schedule'),
    path('standings/', standings, name='standings'),
    
]