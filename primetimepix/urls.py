# primetimepix/urls.py
from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('games/', include('apps.games.urls')),
    path('leagues/', include('apps.leagues.urls')),
    path('picks/', include('apps.picks.urls')),
    path('users/', include('apps.users.urls')),
    path('', include('apps.users.urls')),  # Redirect root to users app
    path('dashboard/', views.dashboard, name='dashboard'),
]
