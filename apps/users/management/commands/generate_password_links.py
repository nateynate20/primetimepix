from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.contrib.auth.forms import PasswordResetForm
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.conf import settings
from apps.users.models import Profile


class Command(BaseCommand):
    help = "Generate password reset links and send reset emails for first-time users"

    def handle(self, *args, **options):
        self.stdout.write("=== PASSWORD RESET LINKS & EMAILS ===")

        users = User.objects.filter(
            is_superuser=False,
            is_active=True,
            last_login__isnull=True  # never logged in
        ).exclude(email="")

        if not users.exists():
            self.stdout.write("No users need password reset links (all have logged in already).")
            return

        sent, skipped, failed = [], [], []

        for user in users:
            profile, _ = Profile.objects.get_or_create(user=user)

            # Skip if already sent
            if profile.password_reset_sent:
                skipped.append(user.email)
                self.stdout.write(self.style.WARNING(f"[SKIP] Already sent to {user.email}"))
                continue

            # Generate reset link
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            reset_link = f"https://primetimepix.onrender.com/users/reset/{uid}/{token}/"

            self.stdout.write(f"User: {user.username}")
            self.stdout.write(f"Email: {user.email}")
            self.stdout.write(f"Reset Link: {reset_link}")
            self.stdout.write("-" * 60)

            # Try sending email
            try:
                form = PasswordResetForm({"email": user.email})
                if form.is_valid():
                    form.save(
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        email_template_name="registration/password_reset_email.html",
                        subject_template_name="registration/password_reset_subject.txt",
                    )
                    profile.password_reset_sent = True
                    profile.save(update_fields=["password_reset_sent"])
                    sent.append(user.email)
                    self.stdout.write(self.style.SUCCESS(f"[EMAIL SENT] {user.email}"))
                else:
                    failed.append({"user": user.email, "error": form.errors})
                    self.stdout.write(self.style.ERROR(f"[FAIL] Invalid form for {user.email}: {form.errors}"))
            except Exception as e:
                failed.append({"user": user.email, "error": str(e)})
                self.stdout.write(self.style.ERROR(f"[ERROR] {user.email}: {e}"))

        # Summary
        summary = {
            "total_checked": users.count(),
            "emails_sent": len(sent),
            "emails_skipped": len(skipped),
            "emails_failed": len(failed),
        }

        self.stdout.write(self.style.NOTICE("=== SUMMARY ==="))
        self.stdout.write(str(summary))

        # Show how many already logged in
        logged_in_users = User.objects.filter(is_superuser=False, last_login__isnull=False).count()
        if logged_in_users > 0:
            self.stdout.write(f"Skipped {logged_in_users} users who have already logged in")
