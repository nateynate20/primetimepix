from django.contrib import admin
from .models import League, LeagueMembership, LeagueCreationRequest, LeagueJoinRequest

@admin.register(League)
class LeagueAdmin(admin.ModelAdmin):
    list_display = ('name', 'sport', 'commissioner', 'is_private', 'is_approved', 'created_at')
    list_filter = ('sport', 'is_private', 'is_approved')
    search_fields = ('name', 'commissioner__username')
    fields = ('name', 'commissioner', 'sport', 'description', 'is_private', 'is_approved')
    readonly_fields = ('created_at',)

@admin.register(LeagueMembership)
class LeagueMembershipAdmin(admin.ModelAdmin):
    list_display = ('user', 'league', 'joined_at')
    list_filter = ('league', 'joined_at')
    search_fields = ('user__username', 'league__name')

@admin.register(LeagueCreationRequest)
class LeagueCreationRequestAdmin(admin.ModelAdmin):
    list_display = ('league_name', 'user', 'approved', 'created_at')
    list_filter = ('approved', 'created_at')
    search_fields = ('league_name', 'user__username')

@admin.register(LeagueJoinRequest)
class LeagueJoinRequestAdmin(admin.ModelAdmin):
    list_display = ('user', 'league', 'created_at', 'approved')
    list_filter = ('approved', 'created_at')
    search_fields = ('user__username', 'league__name')