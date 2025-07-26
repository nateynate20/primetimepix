from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from import_export.admin import ExportMixin
from import_export import resources
from .models import Player, LeagueCreationRequest

# Custom filter for approval status
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

# Import-Export resource for Player model
class PlayerResource(resources.ModelResource):
    class Meta:
        model = Player
        fields = ('id', 'username', 'email', 'team_name')

# Import-Export resource for LeagueCreationRequest model
class LeagueCreationRequestResource(resources.ModelResource):
    class Meta:
        model = LeagueCreationRequest
        fields = ('id', 'league_name', 'user__username', 'created_at', 'approved')

@admin.register(Player)
class PlayerAdmin(ExportMixin, admin.ModelAdmin):
    resource_class = PlayerResource
    list_display = ('username', 'email', 'team_name')
    list_editable = ('team_name',)
    search_fields = ('username', 'team_name', 'email')
    list_filter = ('team_name',)
    ordering = ('username',)
    list_per_page = 25
    fieldsets = (
        (None, {
            'fields': ('user', 'username', 'email'),
        }),
        (_('Team Information'), {
            'fields': ('team_name',),
            'classes': ('collapse',),
        }),
    )

@admin.register(LeagueCreationRequest)
class LeagueCreationRequestAdmin(ExportMixin, admin.ModelAdmin):
    resource_class = LeagueCreationRequestResource
    autocomplete_fields = ['user']
    list_display = ('league_name', 'user', 'created_at', 'approved')
    list_filter = (ApprovedFilter, 'created_at')
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

# Customize the admin site headers
admin.site.site_header = "NFLPIX Admin Portal"
admin.site.site_title = "NFLPIX Admin"
admin.site.index_title = "Welcome to NFLPIX Administration"
