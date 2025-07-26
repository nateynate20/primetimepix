from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin as DefaultUserAdmin

from .models import Profile, Player, LeagueCreationRequest


# Inline Profile for User
class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name_plural = 'Profile'


# Inline Player for User
class PlayerInline(admin.StackedInline):
    model = Player
    can_delete = False
    verbose_name_plural = 'Player Info'


# Extend the default UserAdmin to include Profile and Player
class UserAdmin(DefaultUserAdmin):
    inlines = [ProfileInline, PlayerInline]
    list_display = ('username', 'email', 'is_staff', 'is_active')
    search_fields = ('username', 'email')
    list_filter = ('is_staff', 'is_active', 'date_joined')


# Customize Profile admin
@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'team_name')
    search_fields = ('user__username', 'team_name')


# Customize Player admin
@admin.register(Player)
class PlayerAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'team_name')
    search_fields = ('username', 'email', 'team_name')


# Customize LeagueCreationRequest admin
@admin.register(LeagueCreationRequest)
class LeagueCreationRequestAdmin(admin.ModelAdmin):
    list_display = ('league_name', 'user', 'approved', 'created_at')
    list_filter = ('approved', 'created_at')
    search_fields = ('league_name', 'user__username')
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)


# Unregister the original User admin and register the customized one
admin.site.unregister(User)
admin.site.register(User, UserAdmin)
