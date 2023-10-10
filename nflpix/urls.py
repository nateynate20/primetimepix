# project/urls.py
from django.contrib import admin
from django.urls import path, include
#from nflpix.views import landing_page

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('nfl_schedule.urls')),
    path('nfl_schedule/', include('nfl_schedule.urls')),
]

