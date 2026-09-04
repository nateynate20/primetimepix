from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth import get_user_model
from django.template.loader import render_to_string

from apps.games.models import Game
from apps.games.utils import get_current_nfl_week
from apps.users.models import Notification, ReminderLog
from apps.users.reminders import awareness_email_sent_today

User = get_user_model()


class Command(BaseCommand):
    help = (
        "Send the weekly 'make your picks' reminder — a single overview of the "
        "week's primetime slate. Sent once per week (deduped); the per-game "
        "day-before / morning-of / hours-before nudges live in send_pick_reminders."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run', action='store_true',
            help='Show what would be sent without actually sending.',
        )
        parser.add_argument(
            '--week', type=int,
            help='Override week number (default: current week).',
        )
        parser.add_argument(
            '--user', type=str,
            help='Only send to this username or email (for testing in production).',
        )
        parser.add_argument(
            '--force', action='store_true',
            help=(
                'Send even if the weekly reminder already went out, and do NOT '
                'record a ReminderLog (so the real weekly send is unaffected). '
                'Intended for test sends.'
            ),
        )

    def handle(self, *args, **options):
        dry_run = options.get('dry_run')
        week_override = options.get('week')
        target_user = options.get('user')
        force = options.get('force')
        test_mode = bool(target_user or force)

        current_week = week_override or get_current_nfl_week()

        games = [
            g for g in Game.objects.filter(
                game_type='regular', week=current_week, status='scheduled'
            ).order_by('start_time')
            if g.is_primetime
        ]
        if not games:
            self.stdout.write("No upcoming primetime games this week.")
            return
        season = games[0].season

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

        subject = f"PrimeTimePix: Week {current_week} primetime picks are open"
        self.stdout.write(
            f"Weekly reminder for Week {current_week} ({len(games)} primetime game"
            f"{'s' if len(games) != 1 else ''})"
        )

        sent_count = 0
        skipped_count = 0
        for user in users:
            already = ReminderLog.objects.filter(
                user=user, reminder_type='weekly', game__isnull=True,
                week=current_week, season=season,
            ).exists()
            if already and not force:
                skipped_count += 1
                continue

            # Frequency cap: never stack two awareness emails in one day. The
            # weekly is scheduled early Tuesday so it wins this check over a
            # same-day day-before nudge.
            if not force and awareness_email_sent_today(user):
                skipped_count += 1
                continue

            if dry_run:
                self.stdout.write(f"  Would send to {user.username} ({user.email}): {subject}")
                sent_count += 1
                continue

            email_sent = False
            if user.email:
                try:
                    html_message = render_to_string('emails/weekly_reminder.html', {
                        'user': user,
                        'week': current_week,
                        'games': games,
                        'site_name': settings.SITE_NAME,
                        'site_url': settings.SITE_URL,
                        'picks_url': f"{settings.SITE_URL}/picks/?week={current_week}",
                    })
                    plain = (
                        f"Hey {user.username}, Week {current_week} primetime games are here. "
                        f"Make your picks: {settings.SITE_URL}/picks/?week={current_week}"
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

            if not force:
                Notification.objects.create(
                    user=user, notification_type='pick_reminder',
                    title=subject,
                    message=f"Week {current_week} primetime games are open — make your picks!",
                    link='/picks/',
                )
                ReminderLog.objects.create(
                    user=user, reminder_type='weekly', game=None,
                    week=current_week, season=season,
                    sent_via_email=email_sent, sent_via_app=True,
                )

            sent_count += 1
            self.stdout.write(f"  Sent to {user.username} (email: {email_sent})")

        self.stdout.write(self.style.SUCCESS(
            f"Done. Sent: {sent_count}, Skipped: {skipped_count}"
        ))
