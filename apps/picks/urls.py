# apps/picks/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.display_nfl_schedule, name='schedule'),
    path('standings/', views.standings, name='standings'),
    path('general-standings/', views.general_standings, name='general_standings'),
    path('vs-cpu/', views.vs_cpu, name='vs_cpu'),
    path('toggle-cpu/', views.toggle_cpu_challenge, name='toggle_cpu_challenge'),
]
