# nflpix/urls.py
from django.contrib import admin
from django.urls import path, include
from . import views


urlpatterns = [
    path('admin/', admin.site.urls),
    path('nfl_schedule/', views.display_nfl_schedule, name='nfl_schedule'),
    path('', views.landing_page, name='landing_page'),
    path('players/', include('django.contrib.auth.urls')),
    path('players/', include('players.urls')),

   
]
