<<<<<<< HEAD
#apps/games/urls.py
=======
# apps/games/urls.py
>>>>>>> 80abcf7c5cfbf6c12ebf84c535599e472ccfb913
from django.urls import path
from . import views

urlpatterns = [
    path('schedule/', views.view_schedule_page, name='schedule'),
    path('scores/', views.view_score, name='view_score'),
]
