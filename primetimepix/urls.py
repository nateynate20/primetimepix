# primetimepix/urls.py
from django.contrib import admin
from django.urls import path, include
from django.contrib.auth.views import LogoutView
from apps.users import views as user_views
from apps.picks import views as picks_views
from . import views

urlpatterns = [
    path('admin/', admin.site.urls),

    # App namespaced routes (existing)
    path('games/', include('apps.games.urls')),
    path('leagues/', include('apps.leagues.urls')),
    path('picks/', include('apps.picks.urls')),
    path('users/', include('apps.users.urls')),

    # Short root-level URLs for clean sharing
    path('signup/', user_views.signup, name='signup_short'),
    path('login/', user_views.login_user, name='login_short'),
    path('logout/', LogoutView.as_view(next_page='landing_page'), name='logout_short'),
    path('dashboard/', user_views.dashboard, name='dashboard_short'),
    path('profile/', user_views.edit_profile, name='profile_short'),
    path('standings/', picks_views.general_standings, name='standings_short'),
    path('leaderboard/', picks_views.general_standings, name='leaderboard_short'),

    # Landing page (must be last)
    path('', views.landing_page, name='landing_page'),
]
