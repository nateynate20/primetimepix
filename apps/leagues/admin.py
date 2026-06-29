from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import League, LeagueMembership, LeagueCreationRequest, LeagueJoinRequest


@admin.register(League)
class LeagueAdmin(ModelAdmin):
    list_display = ('name', 'sport', 'commissioner', 'is_private', 'is_approved', 'created_at')
    list_filter = ('sport', 'is_private', 'is_approved')
    search_fields = ('name', 'commissioner__username')
    fields = ('name', 'commissioner', 'sport', 'description', 'is_private', 'is_approved')
    readonly_fields = ('created_at',)


@admin.register(LeagueMembership)
class LeagueMembershipAdmin(ModelAdmin):
    list_display = ('user', 'league', 'joined_at')
    list_filter = ('league', 'joined_at')
    search_fields = ('user__username', 'league__name')


@admin.register(LeagueCreationRequest)
class LeagueCreationRequestAdmin(ModelAdmin):
    list_display = ('league_name', 'user', 'approved', 'created_at')
    list_filter = ('approved', 'created_at')
    search_fields = ('league_name', 'user__username')


@admin.register(LeagueJoinRequest)
class LeagueJoinRequestAdmin(ModelAdmin):
    list_display = ('user', 'league', 'created_at', 'approved')
    list_filter = ('approved', 'created_at')
    search_fields = ('user__username', 'league__name')
