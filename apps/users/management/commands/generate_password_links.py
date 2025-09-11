from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes

class Command(BaseCommand):
    help = 'Generate password reset links for users who have never logged in'

    def handle(self, *args, **options):
        self.stdout.write("=== PASSWORD RESET LINKS ===")
        
        # Only get users who have never logged in (last_login is None)
        # and have email addresses but aren't superusers
        users = User.objects.filter(
            is_superuser=False,
            last_login__isnull=True  # Never logged in
        ).exclude(email='')
        
        if not users.exists():
            self.stdout.write("No users need password reset links (all have logged in already).")
            return
        
        for user in users:
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            reset_link = f"https://primetimepix.onrender.com/users/reset/{uid}/{token}/"
            
            self.stdout.write(f"User: {user.username}")
            self.stdout.write(f"Email: {user.email}")
            self.stdout.write(f"Login Link: {reset_link}")
            self.stdout.write("-" * 60)
        
        self.stdout.write(f"\nGenerated {users.count()} password reset links for first-time users")
        
        # Show count of users who already logged in
        logged_in_users = User.objects.filter(
            is_superuser=False,
            last_login__isnull=False
        ).count()
        
        if logged_in_users > 0:
            self.stdout.write(f"Skipped {logged_in_users} users who have already logged in")