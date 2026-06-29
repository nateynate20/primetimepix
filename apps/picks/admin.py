from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import Pick, CPUPick, UserStats, LeagueStats


@admin.register(Pick)
class PickAdmin(ModelAdmin):
    list_display = ('user', 'game_display', 'picked_team', 'is_correct', 'points', 'league', 'created_at')
    list_filter = ('is_correct', 'game__week', 'game__season', 'league')
    search_fields = ('user__username', 'picked_team', 'game__home_team', 'game__away_team')
    raw_id_fields = ('user', 'game', 'league')
    list_per_page = 50
    ordering = ('-created_at',)

    def game_display(self, obj):
        return f"Wk{obj.game.week}: {obj.game.away_team} @ {obj.game.home_team}"
    game_display.short_description = 'Game'


@admin.register(CPUPick)
class CPUPickAdmin(ModelAdmin):
    list_display = ('game_display', 'picked_team', 'is_correct', 'created_at')
    list_filter = ('is_correct', 'game__week')
    search_fields = ('picked_team',)
    raw_id_fields = ('game',)

    def game_display(self, obj):
        return f"Wk{obj.game.week}: {obj.game.away_team} @ {obj.game.home_team}"
    game_display.short_description = 'Game'


@admin.register(UserStats)
class UserStatsAdmin(ModelAdmin):
    list_display = ('user', 'total_picks', 'correct_picks', 'win_percentage', 'total_points', 'best_streak')
    list_filter = ('win_percentage',)
    search_fields = ('user__username',)
    ordering = ('-total_points',)


@admin.register(LeagueStats)
class LeagueStatsAdmin(ModelAdmin):
    list_display = ('user', 'league', 'total_picks', 'correct_picks', 'win_percentage', 'total_points', 'rank')
    list_filter = ('league',)
    search_fields = ('user__username', 'league__name')
    ordering = ('league', '-total_points')
