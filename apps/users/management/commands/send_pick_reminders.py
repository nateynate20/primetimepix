from datetime import timedelta

import pytz
from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.template.loader import render_to_string

from apps.games.models import Game
from apps.games.utils import get_current_nfl_week
from apps.picks.models import Pick
from apps.users.models import Notification, ReminderLog
from apps.users.reminders import awareness_email_sent_today

User = get_user_model()

EASTERN = pytz.timezone('US/Eastern')


class Command(BaseCommand):
    help = (
        'Send pick reminders for each specific upcoming primetime game. Every '
        'game gets its own day-before / morning-of / hours-before nudge, and '
        'each is deduped independently so users only hear about games they '
        "haven't picked yet."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--type', type=str, choices=['day_before', 'morning_of', 'hours_before'],
            help='Only send this reminder type (default: auto-detect per game).',
        )
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
                'Send even if the user already picked the game or was already '
                'reminded, and do NOT record a ReminderLog (so real scheduled '
                'reminders are unaffected). Targets the next upcoming game only. '
                'Intended for test sends.'
            ),
        )

    def handle(self, *args, **options):
        dry_run = options.get('dry_run')
        forced_type = options.get('type')
        week_override = options.get('week')
        target_user = options.get('user')
        force = options.get('force')
        # A "test send" surfaces email errors instead of silently swallowing
        # them, so you can confirm Brevo delivery in production.
        test_mode = bool(target_user or force)

        now = timezone.now()
        current_week = week_override or get_current_nfl_week()

        primetime_games = [
            g for g in Game.objects.filter(
                game_type='regular', week=current_week, status='scheduled'
            ).order_by('start_time')
            if g.is_primetime
        ]
        if not primetime_games:
            self.stdout.write("No upcoming primetime games this week.")
            return

        recipients = self._recipients(target_user)
        if recipients is None:
            return

        work = self._work_items(primetime_games, now, forced_type, force)
        if not work:
            self.stdout.write(
                f"No primetime game is in a reminder window right now (Week {current_week})."
            )
            return

        sent_count = 0
        skipped_count = 0
        for game, rtype in work:
            self.stdout.write(
                f"'{rtype}' reminder for {game.away_team} @ {game.home_team} "
                f"(kickoff {self._fmt(game, '%a %b %d %I:%M %p ET')})"
            )
            for user in recipients:
                result = self._remind(
                    user, game, rtype, current_week, now, dry_run, force, test_mode
                )
                if result == 'sent':
                    sent_count += 1
                elif result == 'skipped':
                    skipped_count += 1

        self.stdout.write(self.style.SUCCESS(
            f"Done. Sent: {sent_count}, Skipped: {skipped_count}"
        ))

    # ------------------------------------------------------------------ helpers
    def _recipients(self, target_user):
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
                return None
        else:
            users = users.filter(profile__email_reminders_enabled=True)
        return list(users)

    def _kickoff(self, game):
        dt = game.start_time
        if timezone.is_naive(dt):
            dt = pytz.UTC.localize(dt)
        return dt

    def _bucket_for(self, time_until):
        """Map time-until-kickoff to a reminder bucket (or None)."""
        if timedelta(0) < time_until <= timedelta(hours=4):
            return 'hours_before'
        if timedelta(hours=4) < time_until <= timedelta(hours=12):
            return 'morning_of'
        if timedelta(hours=12) < time_until <= timedelta(days=1, hours=12):
            return 'day_before'
        return None

    def _work_items(self, games, now, forced_type, force):
        """Return a list of (game, reminder_type) to act on."""
        # Force/test send: one representative email for the next upcoming game.
        if force:
            rtype = forced_type or 'day_before'
            upcoming = [g for g in games if self._kickoff(g) > now]
            game = upcoming[0] if upcoming else games[0]
            return [(game, rtype)]

        work = []
        for game in games:
            time_until = self._kickoff(game) - now
            if time_until <= timedelta(0):
                continue  # already kicked off
            bucket = self._bucket_for(time_until)
            if bucket is None:
                continue
            if forced_type and bucket != forced_type:
                continue
            work.append((game, bucket))
        return work

    def _remind(self, user, game, rtype, week, now, dry_run, force, test_mode):
        # Already picked this specific game?
        if not force and Pick.objects.filter(user=user, game=game).exists():
            return 'skipped'

        # Already reminded for this game + type?
        already = ReminderLog.objects.filter(
            user=user, game=game, reminder_type=rtype
        ).exists()
        if already and not force:
            return 'skipped'

        # Frequency cap: day-before is an "awareness" nudge, so hold it if the
        # user already got a weekly/day-before email today (e.g. the Wednesday
        # opener, where the weekly slate already covers this game). Game-day
        # urgency (morning_of / hours_before) is exempt and never capped.
        if rtype == 'day_before' and not force and awareness_email_sent_today(user, now):
            return 'skipped'

        subject, message = self._content(rtype, user, game, week)

        if dry_run:
            self.stdout.write(f"  Would send to {user.username} ({user.email}): {subject}")
            return 'sent'

        email_sent = False
        if user.email:
            try:
                from apps.users.unsubscribe import unsubscribe_url
                html_message = render_to_string('emails/pick_reminder.html', {
                    'username': user.username,
                    'headline': subject,
                    'body_text': self._body_text(rtype, game),
                    'week': week,
                    'matchup_away': game.away_team,
                    'matchup_home': game.home_team,
                    'primetime_label': game.primetime_type,
                    'game_day': self._fmt(game, '%A, %b %d'),
                    'game_time': self._fmt(game, '%I:%M %p ET'),
                    'site_url': settings.SITE_URL,
                    'unsubscribe_url': unsubscribe_url(user),
                })
                send_mail(
                    subject, message, settings.DEFAULT_FROM_EMAIL, [user.email],
                    html_message=html_message,
                    # In a test send, let delivery errors raise so you can see
                    # exactly why Brevo rejected/failed.
                    fail_silently=not test_mode,
                )
                email_sent = True
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  Email failed for {user.username}: {e}"))
        elif test_mode:
            self.stdout.write(self.style.WARNING(
                f"  {user.username} has no email address on file — nothing to send."
            ))

        # A forced test send is a no-op on real scheduling: skip the in-app
        # notification and the ReminderLog so genuine reminders still fire later
        # (and the test can be repeated).
        if not force:
            Notification.objects.create(
                user=user, notification_type='pick_reminder',
                title=subject, message=message, link='/picks/',
            )
            ReminderLog.objects.create(
                user=user, reminder_type=rtype, game=game,
                week=week, season=game.season,
                sent_via_email=email_sent, sent_via_app=True,
            )

        self.stdout.write(f"  Sent to {user.username} (email: {email_sent})")
        return 'sent'

    def _fmt(self, game, fmt):
        return self._kickoff(game).astimezone(EASTERN).strftime(fmt)

    def _content(self, rtype, user, game, week):
        matchup = f"{game.away_team} @ {game.home_team}"
        when = f"{self._fmt(game, '%A')} at {self._fmt(game, '%I:%M %p ET')}"
        url = f"{settings.SITE_URL}/picks/?week={week}"

        if rtype == 'day_before':
            subject = f"PrimeTimePix: Pick {matchup} — locks tomorrow"
            message = (
                f"Hey {user.username},\n\n"
                f"Don't forget to pick {matchup}.\n"
                f"Kickoff is {when} — your pick locks at kickoff.\n\n"
                f"Make your pick: {url}\n\nGood luck!\nPrimeTimePix"
            )
        elif rtype == 'morning_of':
            subject = f"PrimeTimePix: Game day — pick {matchup}"
            message = (
                f"Hey {user.username},\n\n"
                f"It's game day! You haven't picked {matchup} yet.\n"
                f"Kickoff is {when}. Don't miss out!\n\n"
                f"Make your pick: {url}\n\nGood luck!\nPrimeTimePix"
            )
        else:  # hours_before
            subject = f"PrimeTimePix: Last call — {matchup} locks soon"
            message = (
                f"Hey {user.username},\n\n"
                f"Last chance to pick {matchup}!\n"
                f"Kickoff is {when} — pick now before it locks.\n\n"
                f"Make your pick: {url}\n\nPrimeTimePix"
            )
        return subject, message

    def _body_text(self, rtype, game):
        matchup = f"{game.away_team} @ {game.home_team}"
        if rtype == 'day_before':
            return f"don't forget to lock in your pick for {matchup} — it kicks off tomorrow."
        if rtype == 'morning_of':
            return f"it's game day and you haven't picked {matchup} yet. Get your pick in before kickoff!"
        return f"last chance — your pick for {matchup} locks in a few hours."
