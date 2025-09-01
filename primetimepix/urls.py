# primetimepix/urls.py
from django.contrib import admin
from django.urls import path, include
<<<<<<< HEAD
from apps.nflpix.views import landing_page
from apps.players.views import dashboard
from apps.picks.views import display_nfl_schedule

=======
from primetimepix.views import landing_page
from apps.users.views import dashboard 

>>>>>>> 80abcf7c5cfbf6c12ebf84c535599e472ccfb913
urlpatterns = [
    path('grappelli/', include('grappelli.urls')),
    path('admin/', admin.site.urls),
<<<<<<< HEAD

    path('', landing_page, name='landing_page'),
=======

    path('', landing_page, name='landing_page'),  # Home page

    path('players/', include('apps.users.urls')),  # Fixed to include your users app URLs correctly

>>>>>>> 80abcf7c5cfbf6c12ebf84c535599e472ccfb913
    path('dashboard/', dashboard, name='dashboard'),
<<<<<<< HEAD

    path('games/', include('apps.games.urls')),
    path('leagues/', include('apps.leagues.urls')),
    path('picks/', include('apps.picks.urls')),
    path('users/', include('apps.users.urls')),

    path('accounts/', include('django.contrib.auth.urls')),
=======

    path('game_picks/', include('apps.picks.urls')),  # Picks app urls

    path('schedule/', include('apps.games.urls')),    # NFL schedule app urls

     path('leagues/', include('apps.leagues.urls')), 
>>>>>>> 80abcf7c5cfbf6c12ebf84c535599e472ccfb913
]
