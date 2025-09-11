# primetimepix/urls.py
from django.contrib import admin
from django.urls import path, include
from apps.users import views as user_views
from . import views   # <-- your landing_page view is here

urlpatterns = [
    path('admin/', admin.site.urls),
    path('grappelli/', include('grappelli.urls')), 
    path('games/', include('apps.games.urls')),
    path('leagues/', include('apps.leagues.urls')),
    path('picks/', include('apps.picks.urls')),
    path('users/', include('apps.users.urls')),
    path('', views.landing_page, name='landing_page'),  # <--- FIXED
]
