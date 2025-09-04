#apps/games/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('schedule/', views.weekly_primetime_view, name='schedule'),
    path('scores/', views.weekly_score_view, name='view_score'),
]

