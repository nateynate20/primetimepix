from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
from django.contrib.auth.views import LogoutView

urlpatterns = [
    path('dashboard/', views.dashboard, name='dashboard'),
    path('login/', views.login_user, name='login'),  # Changed from login_user to login
    path('login_user/', views.login_user, name='login_user'),  # Keep for backwards compatibility
    path('signup/', views.signup, name='signup'),
    path('logout/', LogoutView.as_view(next_page='landing_page'), name='logout'),

    # Password Reset URLs with custom settings
    path('password_reset/', 
         auth_views.PasswordResetView.as_view(
             template_name='registration/password_reset.html',
             email_template_name='registration/password_reset_email.html',
             html_email_template_name='emails/password_reset.html',
             subject_template_name='registration/password_reset_subject.txt',
             success_url='/users/password_reset/done/'
         ), 
         name='password_reset'),
    
    path('password_reset/done/', 
         auth_views.PasswordResetDoneView.as_view(
             template_name='registration/password_reset_done.html'
         ), 
         name='password_reset_done'),
    
    path('reset/<uidb64>/<token>/', 
         auth_views.PasswordResetConfirmView.as_view(
             template_name='registration/password_reset_confirm.html',
             success_url='/users/reset/done/'
         ), 
         name='password_reset_confirm'),
    
    path('reset/done/', 
         auth_views.PasswordResetCompleteView.as_view(
             template_name='registration/password_reset_complete.html'
         ), 
         name='password_reset_complete'),
    
    path('dismiss-notifications/', views.dismiss_notifications, name='dismiss_notifications'),
    path('toggle-reminders/', views.toggle_reminders, name='toggle_reminders'),
    path('profile/', views.edit_profile, name='edit_profile'),
]