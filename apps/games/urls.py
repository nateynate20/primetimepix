# apps/games/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.view_schedule_page, name='schedule'),  # <-- empty path, name is 'schedule'
]
