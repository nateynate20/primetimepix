# apps/leagues/urls.py - Updated with new routes

from django.urls import path
from . import views

urlpatterns = [
    # Public league list and joining
    path('', views.league_list, name='league_list'),
    path('join/<int:league_id>/', views.join_league_instant, name='join_league_instant'),
    path('create/', views.create_league, name='create_league'),
    
    # My leagues and management
    path('my-leagues/', views.my_leagues, name='my_leagues'),
    path('league/', views.select_league, name='league_detail_no_id'),  # Keep for compatibility
    path('league/<int:league_id>/', views.league_detail, name='league_detail'),
    
    # Request management
    path('my-requests/', views.my_league_requests, name='my_league_requests'),
    path('approve-request/<int:request_id>/', views.approve_join_request, name='approve_join_request'),
    path('deny-request/<int:request_id>/', views.deny_join_request, name='deny_join_request'),
    
    # Legacy/admin routes
    path('request-create/', views.request_create_league, name='league_create_request'),
    path('request-join/', views.request_join_league, name='request_join_league'),
    path('creation-requests/', views.review_league_creation_requests, name='creation_requests_list'),
    path('join-requests/', views.review_league_join_requests, name='join_requests_list'),
]