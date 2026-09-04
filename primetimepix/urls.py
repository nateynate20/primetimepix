# primetimepix/urls.py
from django.contrib import admin
from django.urls import path, include
from django.contrib.auth.views import LogoutView
from apps.users import views as user_views
from apps.picks import views as picks_views
from apps.leagues import views as league_views
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

    # Short, shareable league invite links: /join/<code>/
    path('join/<str:code>/', league_views.join_via_invite, name='join_via_invite'),

    # Public, no-login read-only standings (shareable): /standings/<code>/
    path('standings/<str:code>/', league_views.public_standings, name='public_standings'),

    # SEO
    path('robots.txt', views.robots_txt, name='robots_txt'),
    path('sitemap.xml', views.sitemap_xml, name='sitemap_xml'),

    # Legal + email compliance (root-level for clean links in footer/emails)
    path('privacy/', views.privacy_policy, name='privacy'),
    path('terms/', views.terms_of_service, name='terms'),
    path('unsubscribe/', views.unsubscribe, name='unsubscribe_self'),
    path('unsubscribe/<str:token>/', views.unsubscribe, name='unsubscribe'),

    # Staff-only endpoint to verify Sentry captures 500s (see primetimepix/views.py)
    path('debug/sentry-test/', views.sentry_debug, name='sentry_debug'),

    # Landing page (must be last)
    path('', views.landing_page, name='landing_page'),
]
