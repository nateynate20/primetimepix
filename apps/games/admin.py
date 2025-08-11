#apps/games/admin.py

from django.contrib import admin
from .models import Game

@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    list_display = ('game_week', 'home_team', 'away_team', 'start_time', 'status')
    list_filter = ('game_week', 'status')
    search_fields = ('home_team', 'away_team')
