from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from .models import Profile

# Unregister the default User admin
admin.site.unregister(User)

# Create a simple inline for Profile
class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name_plural = 'Profile'

# Register User with Profile inline
@admin.register(User)
class CustomUserAdmin(UserAdmin):
    inlines = (ProfileInline,)
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff')

# Add this to your existing ProfileAdmin
@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'team_name', 'get_email', 'get_last_login', 'get_login_status')
    search_fields = ('user__username', 'team_name', 'user__email')
    list_filter = ('team_name', 'user__last_login')
    
    def get_email(self, obj):
        return obj.user.email
    get_email.short_description = 'Email'
    
    def get_last_login(self, obj):
        return obj.user.last_login.strftime("%m/%d %I:%M%p") if obj.user.last_login else "Never"
    get_last_login.short_description = 'Last Login'
    
    def get_login_status(self, obj):
        return "✅ Active" if obj.user.last_login else "❌ Pending"
    get_login_status.short_description = 'Status'