# apps/games/management/commands/fix_primetime_games.py
from django.core.management.base import BaseCommand
from apps.games.models import Game
import pytz

class Command(BaseCommand):
    help = "Debug and optionally fix primetime games, showing UTC, ET, and primetime info"

    def handle(self, *args, **kwargs):
        eastern = pytz.timezone("US/Eastern")
        updated_count = 0

        self.stdout.write("Game ID | UTC Start | ET Start | Primetime | Primetime Type")
        self.stdout.write("-" * 70)

        for game in Game.objects.all():
            utc_start = game.start_time
            if not utc_start:
                continue

            # Ensure UTC-aware
            if utc_start.tzinfo is None:
                utc_start = pytz.UTC.localize(utc_start)

            et_start = utc_start.astimezone(eastern)
            primetime = game.is_primetime
            primetype = game.primetime_type

            # Print current info
            self.stdout.write(
                f"{game.game_id} | {utc_start.strftime('%Y-%m-%d %H:%M')} | "
                f"{et_start.strftime('%Y-%m-%d %H:%M')} | {primetime} | {primetype}"
            )

            # Optional: Correct primetime start times to 8:20 PM ET for M/Th/Sun games
            weekday = et_start.weekday()  # 0=Mon, 3=Thu, 6=Sun
            if weekday in [0, 3, 6] and primetime:
                corrected_et = et_start.replace(hour=20, minute=20, second=0, microsecond=0)
                corrected_utc = corrected_et.astimezone(pytz.UTC)
                if utc_start != corrected_utc:
                    game.start_time = corrected_utc
                    game.save()
                    updated_count += 1

        self.stdout.write(self.style.SUCCESS(f"\nUpdated {updated_count} games successfully!"))
