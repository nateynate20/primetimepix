# nflpix/urls.py
from django.contrib import admin
from django.urls import path, include
from apps.picks.views import display_nfl_schedule  # Import the view from nfl_schedule app
from nflpix.views import landing_page
from players.views import dashboard
urlpatterns = [
    path('grappelli/', include('grappelli.urls')),
    path('admin/', admin.site.urls),
    path('', landing_page, name='landing_page'),  # Use display_nfl_schedule from nfl_schedule app
    path('players/', include('django.contrib.auth.urls')),
    path('players/', include('players.urls')),
    path('dashboard/', dashboard, name='dashboard'),
    path('game_picks/', include('game_picks.urls')),
    path('schedule/', include('nfl_schedule.urls')),  # Use urls from nfl_schedule app
]
