# nflpix/urls.py
from django.urls import path, include
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.contrib.auth.views import LoginView, LogoutView
from .views import CustomLoginView
from . import views


urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.landing_page, name='landing_page'),
    path('login/', CustomLoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('nfl_schedule/', views.display_nfl_schedule, name='nfl_schedule'),
   
]
