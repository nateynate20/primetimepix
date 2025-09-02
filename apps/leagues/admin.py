from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from import_export.admin import ExportMixin
from import_export import resources

from .models import League, LeagueMembership, LeagueCreationRequest, LeagueJoinRequest

# Filters
class ApprovedFilter(admin.SimpleListFilter):
    title = _('approval status')
    parameter_name = 'approved'

    def lookups(self, request, model_admin):
        return (
            ('approved', _('Approved')),
            ('unapproved', _('Unapproved')),
        )

    def queryset(self, request, queryset):
        if self.value() == 'approved':
            return queryset.filter(approved=True)
        if self.value() == 'unapproved':
            return queryset.filter(approved=False)
        return queryset

# Resources
class LeagueCreationRequestResource(resources.ModelResource):
    class Meta:
        model = LeagueCreationRequest
        fields = ('id', 'league_name', 'user__username', 'created_at', 'approved')

# Admins
@admin.register(League)
class LeagueAdmin(admin.ModelAdmin):
    list_display = ('name', 'sport', 'commissioner', 'created_at', 'is_private')
    search_fields = ('name', 'commissioner__username')
    list_filter = ('sport', 'is_private', 'created_at')

@admin.register(LeagueMembership)
class LeagueMembershipAdmin(admin.ModelAdmin):
    list_display = ('user', 'league', 'joined_at')
    search_fields = ('user__username', 'league__name')
    list_filter = ('joined_at',)

@admin.register(LeagueCreationRequest)
class LeagueCreationRequestAdmin(ExportMixin, admin.ModelAdmin):
    resource_class = LeagueCreationRequestResource
    autocomplete_fields = ['user']
    list_display = ('league_name', 'get_username', 'approved', 'created_at')
    list_filter = ('approved',)
    search_fields = ('league_name', 'user__username')
    ordering = ('-created_at',)
    list_per_page = 25
    readonly_fields = ('created_at',)
    actions = ['approve_leagues', 'unapprove_leagues']

    def approve_leagues(self, request, queryset):
        updated = queryset.update(approved=True)
        self.message_user(request, f"✔️ {updated} league(s) approved.")
    approve_leagues.short_description = "✔️ Mark selected leagues as approved"

    def unapprove_leagues(self, request, queryset):
        updated = queryset.update(approved=False)
        self.message_user(request, f"❌ {updated} league(s) unapproved.")
    unapprove_leagues.short_description = "❌ Mark selected leagues as unapproved"

    def get_username(self, obj):
        return obj.user.username
    get_username.short_description = 'Username'

@admin.register(LeagueJoinRequest)
class LeagueJoinRequestAdmin(admin.ModelAdmin):
    list_display = ('user', 'league', 'created_at', 'approved')
    list_filter = (ApprovedFilter, 'created_at')
    search_fields = ('user__username', 'league__name')
    ordering = ('-created_at',)
    readonly_fields = ('created_at',)
