#apps/users/urls.py
from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
from django.contrib.auth.views import LogoutView

urlpatterns = [
    path('dashboard/', views.dashboard, name='dashboard'),
    path('login_user/', views.login_user, name='login'),
    path('signup/', views.signup, name='signup'),
    path('logout/', LogoutView.as_view(next_page='landing_page'), name='logout'),
    path('test-email/', test_email, name='test_email'),

    # Password Reset URLs
    path('password_reset/', auth_views.PasswordResetView.as_view(template_name='players/password_reset.html'), name='password_reset'),
    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(template_name='players/password_reset_done.html'), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='players/password_reset_confirm.html'), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(template_name='players/password_reset_complete.html'), name='password_reset_complete'),
]

