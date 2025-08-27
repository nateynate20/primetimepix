# apps/games/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('schedule/', views.view_schedule_page, name='schedule'),
    path('scores/', views.view_score, name='view_score'),
]
