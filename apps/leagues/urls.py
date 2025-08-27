from django.urls import path
from . import views

urlpatterns = [
    # League creation requests (superadmin view)
    path('creation-requests/', views.review_league_creation_requests, name='creation_requests_list'),
    
    # League join requests (superadmin view)
    path('join-requests/', views.review_league_join_requests, name='join_requests_list'),

    # League detail views
    path('league/', views.select_league, name='league_detail_no_id'),
    path('league/<int:league_id>/', views.league_detail, name='league_detail'),

    # League creation & join request submission (by users)
    path('request-create/', views.request_create_league, name='league_create_request'),
    path('request-join/', views.request_join_league, name='request_join_league'),  # <-- Added
    path('request-join/<int:league_id>/', views.request_join_league, name='request_join_league'),
]
