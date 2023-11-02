# nflpix/urls.py
from django.urls import path, include
from django.contrib import admin
from . import views


urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.landing_page, name='landing_page'),
    path('nfl_schedule/', views.display_nfl_schedule, name='nfl_schedule'),
   
]
