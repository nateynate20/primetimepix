# primetimepix/urls.py
from django.contrib import admin
from django.urls import path, include
from primetimepix.views import landing_page
from apps.users.views import dashboard 

urlpatterns = [
    path('grappelli/', include('grappelli.urls')),
    path('admin/', admin.site.urls),

    path('', landing_page, name='landing_page'),  # Home page

    path('players/', include('apps.users.urls')),  # Fixed to include your users app URLs correctly

    path('dashboard/', dashboard, name='dashboard'),

    path('game_picks/', include('apps.picks.urls')),  # Picks app urls

    path('schedule/', include('apps.games.urls')),    # NFL schedule app urls

     path('leagues/', include('apps.leagues.urls')), 
]
