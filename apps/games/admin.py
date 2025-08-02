from django.contrib import admin
from .models import Game

class NFLGameAdmin(admin.ModelAdmin):
    list_display = ('week', 'home_team', 'away_team', 'date', 'start_time', 'status')
    list_filter = ('week', 'status')
    search_fields = ('home_team', 'away_team')

admin.site.register(Game, NFLGameAdmin)
