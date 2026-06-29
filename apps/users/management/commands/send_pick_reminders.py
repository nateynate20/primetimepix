from datetime import timedelta
from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.template.loader import render_to_string

from apps.games.models import Game
from apps.games.utils import get_current_nfl_week
from apps.picks.models import Pick
from apps.users.models import Profile, Notification, ReminderLog

User = get_user_model()


class Command(BaseCommand):
    help = 'Send pick reminders to users who have not made their picks'

    def add_arguments(self, parser):
        parser.add_argument(
            '--type', type=str, choices=['day_before', 'morning_of', 'hours_before'],
            help='Specific reminder type to send (default: auto-detect based on time)',
        )
        parser.add_argument(
            '--dry-run', action='store_true',
            help='Show what would be sent without actually sending',
        )
        parser.add_argument(
            '--week', type=int,
            help='Override week number (default: current week)',
        )

    def handle(self, *args, **options):
        dry_run = options.get('dry_run')
        reminder_type = options.get('type')
        week_override = options.get('week')

        now = timezone.now()
        current_week = week_override or get_current_nfl_week()

        # Get primetime games for the current week
        week_games = list(Game.objects.filter(
            game_type='regular', week=current_week, status='scheduled'
        ).order_by('start_time'))
        primetime_games = [g for g in week_games if g.is_primetime]

        if not primetime_games:
            self.stdout.write("No upcoming primetime games this week.")
            return

        first_game = primetime_games[0]
        first_kickoff = first_game.start_time
        if timezone.is_naive(first_kickoff):
            import pytz
            first_kickoff = pytz.UTC.localize(first_kickoff)

        # Auto-detect reminder type based on current time if not specified
        if not reminder_type:
            time_until = first_kickoff - now
            if time_until <= timedelta(hours=4) and time_until > timedelta(hours=0):
                reminder_type = 'hours_before'
            elif time_until <= timedelta(hours=12) and time_until > timedelta(hours=4):
                reminder_type = 'morning_of'
            elif time_until <= timedelta(days=1, hours=12) and time_until > timedelta(hours=12):
                reminder_type = 'day_before'
            else:
                self.stdout.write(f"No reminder needed right now. First kickoff: {first_kickoff}")
                return

        self.stdout.write(f"Sending '{reminder_type}' reminders for Week {current_week}")
        self.stdout.write(f"First kickoff: {first_kickoff}")

        # Determine the current season from games
        season = first_game.season

        # Get users who have NOT picked all primetime games this week
        users = User.objects.filter(
            is_active=True,
            profile__email_reminders_enabled=True
        ).select_related('profile')

        sent_count = 0
        skipped_count = 0

        for user in users:
            # Check if reminder already sent
            already_sent = ReminderLog.objects.filter(
                user=user,
                reminder_type=reminder_type,
                week=current_week,
                season=season
            ).exists()

            if already_sent:
                skipped_count += 1
                continue

            # Check how many picks user has made for this week's primetime games
            user_picks = Pick.objects.filter(
                user=user,
                game__in=primetime_games
            ).count()

            unpicked_count = len(primetime_games) - user_picks

            if unpicked_count <= 0:
                skipped_count += 1
                continue

            # Build reminder content
            subject, message = self._build_reminder_content(
                reminder_type, user, current_week, unpicked_count, len(primetime_games), first_game
            )

            if dry_run:
                self.stdout.write(f"  Would send to {user.username} ({user.email}): {subject}")
                sent_count += 1
                continue

            # Send email
            email_sent = False
            if user.email:
                try:
                    html_message = render_to_string('emails/pick_reminder.html', {
                        'username': user.username,
                        'headline': subject,
                        'body_text': self._get_body_text(reminder_type, unpicked_count, current_week),
                        'week': current_week,
                        'unpicked': unpicked_count,
                        'total': len(primetime_games),
                        'game_day': self._get_game_day(first_game),
                        'game_time': self._get_game_time(first_game),
                        'site_url': settings.SITE_URL,
                    })
                    send_mail(
                        subject,
                        message,
                        settings.DEFAULT_FROM_EMAIL,
                        [user.email],
                        html_message=html_message,
                        fail_silently=True,
                    )
                    email_sent = True
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f"  Email failed for {user.username}: {e}"))

            # Create in-app notification
            Notification.objects.create(
                user=user,
                notification_type='pick_reminder',
                title=subject,
                message=message,
                link='/picks/',
            )

            # Log the reminder
            ReminderLog.objects.create(
                user=user,
                reminder_type=reminder_type,
                week=current_week,
                season=season,
                sent_via_email=email_sent,
                sent_via_app=True,
            )

            sent_count += 1
            self.stdout.write(f"  Sent to {user.username} (email: {email_sent})")

        self.stdout.write(self.style.SUCCESS(
            f"Done. Sent: {sent_count}, Skipped: {skipped_count}"
        ))

    def _build_reminder_content(self, reminder_type, user, week, unpicked, total, first_game):
        """Build subject and message for the reminder."""
        import pytz
        eastern = pytz.timezone('US/Eastern')

        kickoff_et = first_game.start_time
        if timezone.is_naive(kickoff_et):
            kickoff_et = pytz.UTC.localize(kickoff_et)
        kickoff_et = kickoff_et.astimezone(eastern)

        game_day = kickoff_et.strftime('%A')
        game_time = kickoff_et.strftime('%I:%M %p ET')

        if reminder_type == 'day_before':
            subject = f"PrimeTimePix: Week {week} picks lock tomorrow!"
            message = (
                f"Hey {user.username},\n\n"
                f"You have {unpicked} of {total} primetime picks still to make for Week {week}.\n\n"
                f"First game kicks off {game_day} at {game_time} — "
                f"make sure you get your picks in before lockout!\n\n"
                f"Make picks: {settings.SITE_URL}/picks/?week={week}\n\n"
                f"Good luck!\nPrimeTimePix"
            )
        elif reminder_type == 'morning_of':
            subject = f"PrimeTimePix: Game day! {unpicked} pick(s) still open"
            message = (
                f"Hey {user.username},\n\n"
                f"It's game day! You still have {unpicked} primetime pick(s) to make for Week {week}.\n\n"
                f"Kickoff at {game_time} — don't miss out!\n\n"
                f"Make picks: {settings.SITE_URL}/picks/?week={week}\n\n"
                f"Good luck!\nPrimeTimePix"
            )
        else:  # hours_before
            subject = f"PrimeTimePix: Picks lock in a few hours!"
            message = (
                f"Hey {user.username},\n\n"
                f"Last chance! You have {unpicked} pick(s) that lock soon for Week {week}.\n\n"
                f"Kickoff at {game_time} — make your picks NOW!\n\n"
                f"Make picks: {settings.SITE_URL}/picks/?week={week}\n\n"
                f"PrimeTimePix"
            )

        return subject, message

    def _get_body_text(self, reminder_type, unpicked_count, week):
        """Get the body text snippet for the HTML template."""
        if reminder_type == 'day_before':
            return f"you have {unpicked_count} primetime pick(s) still open for Week {week}. First game kicks off tomorrow — make sure you're locked in before kickoff!"
        elif reminder_type == 'morning_of':
            return f"it's game day! You still have {unpicked_count} primetime pick(s) to make for Week {week}. Don't miss out."
        else:
            return f"last chance! You have {unpicked_count} pick(s) that lock in a few hours for Week {week}. Get them in now!"

    def _get_game_day(self, game):
        """Get the formatted game day string."""
        import pytz
        eastern = pytz.timezone('US/Eastern')
        kickoff_et = game.start_time
        if timezone.is_naive(kickoff_et):
            kickoff_et = pytz.UTC.localize(kickoff_et)
        kickoff_et = kickoff_et.astimezone(eastern)
        return kickoff_et.strftime('%A, %b %d')

    def _get_game_time(self, game):
        """Get the formatted game time string."""
        import pytz
        eastern = pytz.timezone('US/Eastern')
        kickoff_et = game.start_time
        if timezone.is_naive(kickoff_et):
            kickoff_et = pytz.UTC.localize(kickoff_et)
        kickoff_et = kickoff_et.astimezone(eastern)
        return kickoff_et.strftime('%I:%M %p ET')
