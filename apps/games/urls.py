from django.urls import path
from . import views

app_name = 'nfl_schedule'

urlpatterns = [
    path('schedule/', views.view_schedule_page, name='view_schedule_page'),
]
