from django.urls import path
from . import views

urlpatterns = [
    # Existing URLs
    path('creation-requests/', views.review_league_creation_requests, name='creation_requests_list'),
    path('join-requests/', views.review_league_join_requests, name='join_requests_list'),
    path('league/', views.select_league, name='league_detail_no_id'),
    path('league/<int:league_id>/', views.league_detail, name='league_detail'),
    path('request-create/', views.request_create_league, name='league_create_request'),
    path('request-join/', views.request_join_league, name='request_join_league'),
    path('request-join/<int:league_id>/', views.request_join_league, name='request_join_league'),
    
    # New URLs for public league list and commissioner management
    path('', views.league_list, name='league_list'),
    path('my-requests/', views.my_league_requests, name='my_league_requests'),
    path('approve-request/<int:request_id>/', views.approve_join_request, name='approve_join_request'),
    path('deny-request/<int:request_id>/', views.deny_join_request, name='deny_join_request'),
    path('join/<int:league_id>/', views.request_join_league, name='join_league'),
]