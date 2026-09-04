from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth import get_user_model
from django.template.loader import render_to_string

from apps.games.models import Game
from apps.games.utils import get_current_nfl_week
from apps.users.models import Notification, ReminderLog
from apps.users.reminders import weekly_recap_for_user

User = get_user_model()


class Command(BaseCommand):
    help = (
        "Send the weekly recap email — 'here's how you did last week' with your "
        "record, points, and rank movement. Retrospective (not a pick nudge), so "
        "it's deduped per week but exempt from the awareness frequency cap."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run', action='store_true',
            help='Show what would be sent without actually sending.',
        )
        parser.add_argument(
            '--week', type=int,
            help='Recap this week number (default: the just-completed week).',
        )
        parser.add_argument(
            '--user', type=str,
            help='Only send to this username or email (for testing in production).',
        )
        parser.add_argument(
            '--force', action='store_true',
            help=(
                'Send even if the recap already went out, and do NOT record a '
                'ReminderLog (so the real send is unaffected). For test sends.'
            ),
        )

    def handle(self, *args, **options):
        dry_run = options.get('dry_run')
        week_override = options.get('week')
        target_user = options.get('user')
        force = options.get('force')
        test_mode = bool(target_user or force)

        # Default to the just-completed week.
        recap_week = week_override or (get_current_nfl_week() - 1)
        if recap_week < 1:
            self.stdout.write("No completed week to recap yet.")
            return

        sample = Game.objects.filter(week=recap_week).order_by('-start_time').first()
        if not sample:
            self.stdout.write(f"No games found for Week {recap_week}.")
            return
        season = sample.season

        users = User.objects.filter(is_active=True).select_related('profile')
        if target_user:
            from django.db.models import Q
            users = users.filter(
                Q(username__iexact=target_user) | Q(email__iexact=target_user)
            )
            if not users.exists():
                self.stderr.write(self.style.ERROR(
                    f"No active user matches --user '{target_user}'."
                ))
                return
        else:
            users = users.filter(profile__email_reminders_enabled=True)

        self.stdout.write(f"Weekly recap for Week {recap_week} (season {season})")

        sent_count = 0
        skipped_count = 0
        for user in users:
            already = ReminderLog.objects.filter(
                user=user, reminder_type='recap', game__isnull=True,
                week=recap_week, season=season,
            ).exists()
            if already and not force:
                skipped_count += 1
                continue

            recap = weekly_recap_for_user(user, recap_week, season)
            if not recap:
                skipped_count += 1
                continue

            subject = f"PrimeTimePix: Your Week {recap_week} recap — {recap['record']}"

            if dry_run:
                self.stdout.write(
                    f"  Would send to {user.username} ({user.email}): "
                    f"{recap['record']}, rank {recap['rank']}/{recap['total_members']} "
                    f"in {recap['league'].name}"
                )
                sent_count += 1
                continue

            email_sent = False
            if user.email:
                try:
                    from apps.users.unsubscribe import unsubscribe_url
                    from django.urls import reverse
                    standings_url = (
                        f"{settings.SITE_URL}"
                        f"{reverse('public_standings', args=[recap['league'].join_code])}"
                    )
                    html_message = render_to_string('emails/weekly_recap.html', {
                        'user': user,
                        'recap': recap,
                        'site_name': settings.SITE_NAME,
                        'site_url': settings.SITE_URL,
                        'standings_url': standings_url,
                        'picks_url': f"{settings.SITE_URL}/picks/",
                        'unsubscribe_url': unsubscribe_url(user),
                    })
                    plain = (
                        f"Week {recap_week} recap for {user.username}: "
                        f"you went {recap['record']} ({recap['week_points']} pts). "
                        f"You're #{recap['rank']} of {recap['total_members']} in "
                        f"{recap['league'].name}. Standings: {standings_url}"
                    )
                    send_mail(
                        subject, plain, settings.DEFAULT_FROM_EMAIL, [user.email],
                        html_message=html_message,
                        fail_silently=not test_mode,
                    )
                    email_sent = True
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"  Email failed for {user.username}: {e}"))
            elif test_mode:
                self.stdout.write(self.style.WARNING(
                    f"  {user.username} has no email address on file — nothing to send."
                ))

            # Second channel: web push (no-op without a subscription / VAPID).
            from apps.users.push import send_web_push
            send_web_push(
                user, subject,
                f"You went {recap['record']} in Week {recap_week} — see where you stand.",
                url='/standings/', tag=f"recap-{recap_week}",
            )

            if not force:
                Notification.objects.create(
                    user=user, notification_type='pick_reminder',
                    title=subject,
                    message=(
                        f"Week {recap_week}: you went {recap['record']} and sit "
                        f"#{recap['rank']} of {recap['total_members']} in {recap['league'].name}."
                    ),
                    link='/standings/',
                )
                ReminderLog.objects.create(
                    user=user, reminder_type='recap', game=None,
                    week=recap_week, season=season,
                    sent_via_email=email_sent, sent_via_app=True,
                )

            sent_count += 1
            self.stdout.write(f"  Sent to {user.username} (email: {email_sent})")

        self.stdout.write(self.style.SUCCESS(
            f"Done. Sent: {sent_count}, Skipped: {skipped_count}"
        ))
