from django.contrib import admin
from .models import Player, LeagueCreationRequest

@admin.register(Player)
class PlayerAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'team_name')
    search_fields = ('username', 'team_name', 'email')
    list_filter = ('team_name',)
    ordering = ('username',)

@admin.register(LeagueCreationRequest)
class LeagueCreationRequestAdmin(admin.ModelAdmin):
    list_display = ('league_name', 'user', 'created_at', 'approved')
    list_filter = ('approved', 'created_at')
    search_fields = ('league_name', 'user__username')
    ordering = ('-created_at',)
    actions = ['approve_leagues', 'unapprove_leagues']

    def approve_leagues(self, request, queryset):
        updated = queryset.update(approved=True)
        self.message_user(request, f"{updated} league(s) approved.")
    approve_leagues.short_description = "Mark selected leagues as approved"

    def unapprove_leagues(self, request, queryset):
        updated = queryset.update(approved=False)
        self.message_user(request, f"{updated} league(s) unapproved.")
    unapprove_leagues.short_description = "Mark selected leagues as unapproved"

# Customize the admin site headers
admin.site.site_header = "NFLPIX Admin"
admin.site.site_title = "NFLPIX Admin Portal"
admin.site.index_title = "Welcome to NFLPIX Admin"
