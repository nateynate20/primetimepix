from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from import_export.admin import ExportMixin
from import_export import resources
from apps.users.models import Profile as Player

class PlayerResource(resources.ModelResource):
    class Meta:
        model = Player
        fields = ('id', 'user__username', 'user__email', 'team_name')

@admin.register(Player)
class PlayerAdmin(ExportMixin, admin.ModelAdmin):
    resource_class = PlayerResource
    list_display = ('user', 'team_name')
    list_editable = ('team_name',)
    search_fields = ('user__username', 'team_name', 'user__email')
    list_filter = ('team_name',)
    ordering = ('user__username',)
    list_per_page = 25
    fieldsets = (
        (None, {'fields': ('user',)}),
        (_('Team Information'), {
            'fields': ('team_name',),
            'classes': ('collapse',),
        }),
    )
