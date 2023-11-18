# nflpix/urls.py
from django.contrib import admin
from django.urls import path, include
from . import views
from nflpix.views import landing_page
from game_picks.views import display_nfl_schedule

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', landing_page, name='landing_page'),
    path('players/', include('django.contrib.auth.urls')),
    path('players/', include('players.urls')),
    path('schedule/', display_nfl_schedule, name='display_nfl_schedule'),
    path('game_picks/', include('game_picks.urls')),

   
]
