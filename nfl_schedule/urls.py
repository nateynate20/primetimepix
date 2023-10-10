# nfl_schedule/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.display_nfl_schedule, name='nfl_schedule'),
]
