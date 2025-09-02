#apps/picks/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('save/', views.save_picks, name='save_picks'),
    path('standings/', views.standings, name='standings'),
]
