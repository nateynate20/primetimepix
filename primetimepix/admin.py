# primetimepix/admin.py
from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from import_export.admin import ExportMixin
from import_export import resources
from .models import Player
from apps.leagues.models import LeagueCreationRequest  # Updated import path


class ApprovedFilter(admin.SimpleListFilter):
    """
    Filter for approval status: approved or unapproved.
    """
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


class PlayerResource(resources.ModelResource):
    class Meta:
        model = Player
        fields = ('id', 'username', 'email', 'team_name')


class LeagueCreationRequestResource(resources.ModelResource):
    class Meta:
        model = LeagueCreationRequest
        fields = ('id', 'league_name', 'user__username', 'created_at', 'approved')


@admin.register(Player)
class PlayerAdmin(ExportMixin, admin.ModelAdmin):
    resource_class = PlayerResource
    list_display = ('get_username', 'get_email', 'points')
    list_filter = ('points',)
    search_fields = ('user__username', 'user__email')
    ordering = ('user__username',)

    def get_username(self, obj):
        return obj.user.username
    get_username.short_description = 'Username'

    def get_email(self, obj):
        return obj.user.email
    get_email.short_description = 'Email'



admin.site.site_header = "NFLPIX Admin Portal"
admin.site.site_title = "NFLPIX Admin"
admin.site.index_title = "Welcome to NFLPIX Administration"

