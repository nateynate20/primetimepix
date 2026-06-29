#apps/games/admin.py
from django.contrib import admin
from .models import Game


@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    list_display = ('week', 'game_type', 'away_team', 'away_score_display', 'home_team', 'home_score_display', 'start_time', 'status', 'is_primetime_display')
    list_filter = ('season', 'week', 'status', 'game_type')
    search_fields = ('home_team', 'away_team', 'game_id')
    list_per_page = 50
    ordering = ('-season', 'week', 'start_time')
    readonly_fields = ('game_id', 'created_at', 'updated_at')

    fieldsets = (
        ('Game Info', {
            'fields': ('game_id', 'season', 'week', 'game_type', 'start_time', 'status')
        }),
        ('Teams & Scores', {
            'fields': ('home_team', 'away_team', 'home_score', 'away_score')
        }),
        ('Spread Data', {
            'fields': ('spread', 'spread_favorite'),
            'classes': ('collapse',),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    def home_score_display(self, obj):
        return obj.home_score if obj.home_score is not None else '-'
    home_score_display.short_description = 'H'

    def away_score_display(self, obj):
        return obj.away_score if obj.away_score is not None else '-'
    away_score_display.short_description = 'A'

    def is_primetime_display(self, obj):
        return obj.primetime_type if obj.is_primetime else ''
    is_primetime_display.short_description = 'Primetime'

    actions = ['mark_as_final', 'recalculate_picks']

    @admin.action(description='Mark selected games as Final')
    def mark_as_final(self, request, queryset):
        updated = queryset.filter(home_score__isnull=False, away_score__isnull=False).update(status='final')
        self.message_user(request, f"{updated} game(s) marked as final.")

    @admin.action(description='Recalculate pick results for selected games')
    def recalculate_picks(self, request, queryset):
        total = 0
        for game in queryset.filter(status='final'):
            total += game.update_pick_results()
        self.message_user(request, f"Recalculated {total} pick(s) across {queryset.count()} game(s).")
