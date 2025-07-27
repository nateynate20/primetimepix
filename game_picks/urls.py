from django.urls import path
from .views import (
    display_nfl_schedule,
    standings,
    request_create_league,
    request_join_league,
    join_league_view,                 # new view for listing leagues to join
    admin_league_creation_requests,
    admin_league_join_requests,
    league_detail,                   # add this import
)

urlpatterns = [
    path('schedule/', display_nfl_schedule, name='schedule'),
    path('standings/', standings, name='standings'),

    # League user actions
    path('league/request-create/', request_create_league, name='request_create_league'),
    path('league/request-join/', request_join_league, name='request_join_league'),

    path('league/join-leagues/', join_league_view, name='join_league_view'),  # new listing page

    path('league/<int:league_id>/', league_detail, name='league_detail'),  # view league details / standings

    # Admin views for moderation
    path('admin/league-creation-requests/', admin_league_creation_requests, name='admin_league_creation_requests'),
    path('admin/league-join-requests/', admin_league_join_requests, name='admin_league_join_requests'),
]
