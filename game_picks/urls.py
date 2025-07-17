from django.urls import path
from .views import (
    display_nfl_schedule,
    standings,
    request_create_league,
    request_join_league,
    admin_league_creation_requests,
    admin_league_join_requests,
)

urlpatterns = [
    path('schedule/', display_nfl_schedule, name='schedule'),
    path('standings/', standings, name='standings'),

    path('league/request-create/', request_create_league, name='request_create_league'),
    path('league/request-join/', request_join_league, name='request_join_league'),

    # Admin URLs
    path('admin/league-creation-requests/', admin_league_creation_requests, name='admin_league_creation_requests'),
    path('admin/league-join-requests/', admin_league_join_requests, name='admin_league_join_requests'),
]
