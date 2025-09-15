# apps/users/management/commands/generate_password_links.py
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.forms import PasswordResetForm
from django.conf import settings
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes

from apps.users.models import Profile


class Command(BaseCommand):
    help = 'Generate password reset links and send emails for users who have never logged in'

    def handle(self, *args, **options):
        self.stdout.write("=== PASSWORD RESET LINKS & EMAILS ===")

        # Users who have never logged in and have email addresses
        users = User.objects.filter(is_superuser=False, last_login__isnull=True).exclude(email='')

        if not users.exists():
            self.stdout.write("No users need password reset links (all have logged in already).")
            return

        for user in users:
            try:
                # Ensure profile exists with a unique team_name
                profile, created = Profile.objects.get_or_create(
                    user=user,
                    defaults={'team_name': f'{user.username}_team'}
                )

                if profile.password_reset_sent:
                    self.stdout.write(f"[SKIP] Already sent to {user.email}")
                    continue

                # Generate reset link for logging
                token = default_token_generator.make_token(user)
                uid = urlsafe_base64_encode(force_bytes(user.pk))
                reset_link = f"https://primetimepix.onrender.com/users/reset/{uid}/{token}/"

                self.stdout.write(f"User: {user.username}")
                self.stdout.write(f"Email: {user.email}")
                self.stdout.write(f"Reset Link: {reset_link}")
                self.stdout.write("-" * 60)

                # Send email
                form = PasswordResetForm({'email': user.email})
                if form.is_valid():
                    form.save(
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        email_template_name='registration/password_reset_email.html',
                        subject_template_name='registration/password_reset_subject.txt',
                        request=None,
                        domain_override='primetimepix.onrender.com',  # avoids get_host() error
                    )

                    # Mark as sent
                    profile.password_reset_sent = True
                    profile.save()

                    self.stdout.write(f"[EMAIL SENT] Reset email sent to: {user.email}")
                else:
                    self.stdout.write(f"[FAIL] Form invalid for {user.email}: {form.errors}")

            except Exception as e:
                self.stdout.write(f"[ERROR] {user.email}: {e}")

        # Summary
        self.stdout.write(f"\nTotal users processed: {users.count()}")
        sent_count = users.filter(profile__password_reset_sent=True).count()
        self.stdout.write(f"Password reset emails sent: {sent_count}")
