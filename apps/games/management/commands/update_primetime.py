# apps/games/management/commands/fix_primetime.py
from django.core.management.base import BaseCommand
from apps.games.models import Game
import pytz

class Command(BaseCommand):
    help = 'Check and display primetime game detection - no database changes'

    def add_arguments(self, parser):
        parser.add_argument(
            '--week',
            type=int,
            help='Check specific NFL week',
        )

    def handle(self, *args, **options):
        week = options.get('week')
        
        if week:
            games = Game.objects.filter(week=week).order_by('start_time')
            self.stdout.write(f"Checking primetime detection for Week {week}...")
        else:
            # Check recent games
            games = Game.objects.all().order_by('start_time')
            self.stdout.write("Checking primetime detection for all games...")
        
        self.stdout.write("-" * 70)
        
        primetime_count = 0
        total_count = 0
        
        for game in games:
            total_count += 1
            et_time = game.display_time_et
            
            if not et_time:
                continue
                
            is_primetime = game.is_primetime
            primetime_type = game.primetime_type
            
            if is_primetime:
                primetime_count += 1
                icon = "⭐"
                style = self.style.SUCCESS
            else:
                icon = "  "
                style = self.style.WARNING
            
            weekday_name = et_time.strftime('%A')
            time_str = et_time.strftime('%I:%M %p')
            
            message = f"{icon} {game.away_team} @ {game.home_team}"
            self.stdout.write(style(message))
            self.stdout.write(f"    {weekday_name} {et_time.strftime('%m/%d')} at {time_str} ET")
            
            if is_primetime:
                self.stdout.write(f"    🎯 PRIMETIME: {primetime_type}")
            else:
                self.stdout.write(f"    Regular game")
            
            self.stdout.write("")
        
        self.stdout.write("-" * 70)
        self.stdout.write(
            self.style.SUCCESS(
                f"SUMMARY: {primetime_count} primetime games out of {total_count} total games"
            )
        )
        
        # Show expected pattern
        self.stdout.write("\nPrimetime Games Should Include:")
        self.stdout.write("✓ Sunday Night Football (Sunday 7:00+ PM ET)")
        self.stdout.write("✓ Monday Night Football (Monday 7:00+ PM ET)")
        self.stdout.write("✓ Thursday Night Football (Thursday 7:00+ PM ET)")
        self.stdout.write("✓ Holiday games (any time)")
        self.stdout.write("✓ Playoff games (any time)")
        
        if primetime_count == 0:
            self.stdout.write(
                self.style.ERROR("\n❌ No primetime games detected!")
            )
            self.stdout.write("\nTroubleshooting steps:")
            self.stdout.write("1. Run: python manage.py debug_primetime")
            self.stdout.write("2. Check if games exist: python manage.py shell -c \"from apps.games.models import Game; print(Game.objects.count())\"")
            self.stdout.write("3. Sync schedule: python manage.py sync_nfl_schedule --week 1")
        else:
            self.stdout.write(
                self.style.SUCCESS(f"\n✅ Found {primetime_count} primetime games!")
            )