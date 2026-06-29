from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from .models import Profile, Notification, ReminderLog

admin.site.unregister(User)


class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name_plural = 'Profile'
    fields = ('team_name', 'cpu_challenge_active', 'email_reminders_enabled')


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    inlines = (ProfileInline,)
    list_display = ('username', 'email', 'get_team_name', 'date_joined', 'last_login', 'is_active')
    list_filter = ('is_active', 'is_staff', 'date_joined')
    search_fields = ('username', 'email', 'profile__team_name')
    ordering = ('-date_joined',)

    def get_team_name(self, obj):
        try:
            return obj.profile.team_name
        except Profile.DoesNotExist:
            return '-'
    get_team_name.short_description = 'Team Name'


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'team_name', 'email_reminders_enabled', 'cpu_challenge_active', 'get_login_status')
    search_fields = ('user__username', 'team_name', 'user__email')
    list_filter = ('email_reminders_enabled', 'cpu_challenge_active')

    def get_login_status(self, obj):
        if obj.user.last_login:
            return obj.user.last_login.strftime("%m/%d/%Y")
        return "Never logged in"
    get_login_status.short_description = 'Last Login'


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'notification_type', 'title', 'is_read', 'created_at')
    list_filter = ('notification_type', 'is_read', 'created_at')
    search_fields = ('user__username', 'title', 'message')
    list_per_page = 50
    ordering = ('-created_at',)
    readonly_fields = ('created_at',)


@admin.register(ReminderLog)
class ReminderLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'reminder_type', 'week', 'season', 'sent_via_email', 'sent_via_app', 'sent_at')
    list_filter = ('reminder_type', 'season', 'week', 'sent_via_email')
    search_fields = ('user__username',)
    list_per_page = 50
    ordering = ('-sent_at',)
    readonly_fields = ('sent_at',)
