from django import forms
from django.contrib import admin, messages
from unfold.admin import ModelAdmin, TabularInline
from .models import League, LeagueMembership, LeagueCreationRequest, LeagueJoinRequest


class LeagueMembershipInline(TabularInline):
    model = LeagueMembership
    extra = 1
    autocomplete_fields = ('user',)
    verbose_name = 'Member'
    verbose_name_plural = 'Members'


class LeagueAdminForm(forms.ModelForm):
    class Meta:
        model = League
        fields = [
            'name', 'commissioner', 'co_commissioners',
            'sport', 'description', 'is_private', 'is_approved',
        ]

    def clean_co_commissioners(self):
        co_commissioners = self.cleaned_data.get('co_commissioners')
        if not co_commissioners:
            return co_commissioners

        # Co-commissioners must already be members of this league.
        if self.instance and self.instance.pk:
            member_ids = set(
                self.instance.members.values_list('id', flat=True)
            )
            member_ids.add(self.instance.commissioner_id)
            invalid = [u for u in co_commissioners if u.id not in member_ids]
            if invalid:
                names = ', '.join(u.username for u in invalid)
                raise forms.ValidationError(
                    f"These users must be members of the league before becoming "
                    f"co-commissioners: {names}."
                )
        return co_commissioners


@admin.register(League)
class LeagueAdmin(ModelAdmin):
    form = LeagueAdminForm
    inlines = (LeagueMembershipInline,)
    list_display = ('name', 'sport', 'commissioner', 'is_private', 'is_approved', 'created_at')
    list_filter = ('sport', 'is_private', 'is_approved')
    search_fields = ('name', 'commissioner__username')
    fields = ('name', 'commissioner', 'co_commissioners', 'sport', 'description', 'is_private', 'is_approved', 'invite_code')
    readonly_fields = ('created_at', 'invite_code')
    filter_horizontal = ('co_commissioners',)


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
    actions = ('approve_requests', 'deny_requests')

    @admin.action(description='Approve selected requests (creates the league)')
    def approve_requests(self, request, queryset):
        created, skipped = 0, 0
        for req in queryset:
            if req.approved:
                skipped += 1
                continue
            # Mirror the in-app approval flow: create the league, set the
            # requester as commissioner, then mark the request approved (which
            # fires the approval-email signal on save).
            League.objects.create(
                name=req.league_name,
                commissioner=req.user,
                description=req.description or '',
                is_approved=True,
                is_private=False,
            )
            req.approved = True
            req.save()
            created += 1
        if created:
            self.message_user(
                request,
                f'Approved {created} request(s) and created the league(s).',
                messages.SUCCESS,
            )
        if skipped:
            self.message_user(
                request,
                f'Skipped {skipped} already-approved request(s).',
                messages.WARNING,
            )

    @admin.action(description='Deny and delete selected requests')
    def deny_requests(self, request, queryset):
        count = queryset.count()
        queryset.delete()
        self.message_user(
            request,
            f'Denied and deleted {count} request(s).',
            messages.WARNING,
        )


@admin.register(LeagueJoinRequest)
class LeagueJoinRequestAdmin(ModelAdmin):
    list_display = ('user', 'league', 'created_at', 'approved')
    list_filter = ('approved', 'created_at')
    search_fields = ('user__username', 'league__name')
