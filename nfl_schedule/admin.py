from django.contrib import admin
from .models import NFLGame


class NFLGameAdmin(admin.ModelAdmin):
    list_display = ('week', 'home_team', 'away_team', 'start_time')
    list_filter = ('week',)
    search_fields = ('home_team', 'away_team')

admin.site.register(NFLGame, NFLGameAdmin)

# Register your models here.
