from django.urls import path
from . import views

urlpatterns = [
    path('import-nfl-schedule/', views.import_nfl_schedule, name='import_nfl_schedule'),
    path('refresh-nfl-scores/', views.htmx_refresh_scores, name='refresh_nfl_scores'),
    path('scores/', views.view_scores_page, name='view_scores_page'),
]
