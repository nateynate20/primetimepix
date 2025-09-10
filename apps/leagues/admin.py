# apps/leagues/admin.py
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

# Inline for League Members
class LeagueMembershipInline(admin.TabularInline):
    model = LeagueMembership
    extra = 1
    autocomplete_fields = ['user']
    readonly_fields = ['joined_at']

# Resources
class LeagueCreationRequestResource(resources.ModelResource):
    class Meta:
        model = LeagueCreationRequest
        fields = ('id', 'league_name', 'user__username', 'created_at', 'approved')

# Admins
@admin.register(League)
class LeagueAdmin(admin.ModelAdmin):
    list_display = ('name', 'sport', 'commissioner', 'member_count', 'is_private', 'is_approved', 'created_at')
    list_filter = ('sport', 'is_private', 'is_approved', 'created_at')
    search_fields = ('name', 'commissioner__username', 'description')
    autocomplete_fields = ['commissioner']
    inlines = [LeagueMembershipInline]
    readonly_fields = ['created_at']
    
    fieldsets = (
        (None, {
            'fields': ('name', 'commissioner', 'sport', 'description')
        }),
        ('Settings', {
            'fields': ('is_private', 'is_approved'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )

    def member_count(self, obj):
        return obj.member_count
    member_count.short_description = 'Members'

    def save_model(self, request, obj, form, change):
        """Override to ensure commissioner is added as member"""
        super().save_model(request, obj, form, change)
        # The signal should handle this, but let's be explicit
        LeagueMembership.objects.get_or_create(
            user=obj.commissioner,
            league=obj
        )

@admin.register(LeagueMembership)
class LeagueMembershipAdmin(admin.ModelAdmin):
    list_display = ('user', 'league', 'joined_at')
    list_filter = ('joined_at', 'league__sport')
    search_fields = ('user__username', 'league__name')
    autocomplete_fields = ['user', 'league']
    readonly_fields = ['joined_at']

@admin.register(LeagueCreationRequest)
class LeagueCreationRequestAdmin(ExportMixin, admin.ModelAdmin):
    resource_class = LeagueCreationRequestResource
    autocomplete_fields = ['user']
    list_display = ('league_name', 'get_username', 'approved', 'created_at')
    list_filter = ('approved', 'created_at')
    search_fields = ('league_name', 'user__username', 'description')
    ordering = ('-created_at',)
    list_per_page = 25
    readonly_fields = ('created_at',)
    actions = ['approve_leagues', 'unapprove_leagues']

    def approve_leagues(self, request, queryset):
        """Approve league creation requests and create actual leagues"""
        created_count = 0
        for req in queryset.filter(approved=False):
            # Create the actual league
            league = League.objects.create(
                name=req.league_name,
                commissioner=req.user,
                description=req.description or '',
                is_approved=True,
                is_private=True
            )
            # Mark request as approved
            req.approved = True
            req.save()
            created_count += 1
        
        self.message_user(request, f"✔️ {created_count} league(s) created and approved.")
    approve_leagues.short_description = "✔️ Approve and create leagues"

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
    list_filter = (ApprovedFilter, 'created_at', 'league__sport')
    search_fields = ('user__username', 'league__name')
    autocomplete_fields = ['user', 'league']
    ordering = ('-created_at',)
    readonly_fields = ('created_at',)
    actions = ['approve_join_requests']

    def approve_join_requests(self, request, queryset):
        """Approve join requests and add users to leagues"""
        approved_count = 0
        for req in queryset.filter(approved=False):
            # Add user to league
            LeagueMembership.objects.get_or_create(
                user=req.user,
                league=req.league
            )
            # Mark request as approved
            req.approved = True
            req.save()
            approved_count += 1
        
        self.message_user(request, f"✔️ {approved_count} join request(s) approved.")
    approve_join_requests.short_description = "✔️ Approve join requests"