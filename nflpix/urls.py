# nflpix/urls.py
from django.urls import path, include
from . import views


urlpatterns = [
    path('', views.landing_page, name='landing_page'),
    path('nfl_schedule/', views.display_nfl_schedule, name='nfl_schedule'),
   
]
