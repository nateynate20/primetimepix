from django.core.management.base import BaseCommand
import nfl_data_py as nfl
from apps.games.models import Game
from django.utils import timezone
from dateutil import parser
from datetime import datetime, time
import pytz
import re

class Command(BaseCommand):
    help = "Sync NFL schedule using nfl_data_py"

    def parse_game_time(self, time_str):
        """Parse various time formats from NFL data"""
        if not time_str or str(time_str).upper() in ['TBD', 'TBA', 'NULL', 'NAN']:
            return time(13, 0, 0)  # Default to 1 PM ET for unknown times
        
        time_str = str(time_str).strip()
        
        # Try different time formats
        time_formats = [
            '%H:%M:%S',     # 20:30:00
            '%H:%M',        # 20:30
            '%I:%M %p',     # 8:30 PM
            '%I:%M:%S %p',  # 8:30:00 PM
        ]
        
        for fmt in time_formats:
            try:
                return datetime.strptime(time_str, fmt).time()
            except ValueError:
                continue
        
        # If all formats fail, try to extract time using regex
        # Look for patterns like "8:30", "20:30", etc.
        time_match = re.search(r'(\d{1,2}):(\d{2})', time_str)
        if time_match:
            hour, minute = int(time_match.group(1)), int(time_match.group(2))
            
            # If it looks like PM time but no AM/PM specified, assume afternoon/evening
            if 'PM' in time_str.upper() or 'P' in time_str.upper():
                if hour != 12:
                    hour += 12
            elif 'AM' in time_str.upper() or 'A' in time_str.upper():
                if hour == 12:
                    hour = 0
            elif hour < 12 and hour >= 1:  # Likely afternoon/evening game
                if hour < 8:  # Likely PM
                    hour += 12
            
            return time(hour, minute, 0)
        
        # Last resort - return default time
        self.stdout.write(
            self.style.WARNING(f"Could not parse time '{time_str}', using default 1 PM ET")
        )
        return time(13, 0, 0)

    def handle(self, *args, **options):
        created, updated, skipped = 0, 0, 0
        now = timezone.now()
        season_year = now.year if now.month >= 8 else now.year - 1
        
        # Use Eastern timezone for NFL games
        eastern = pytz.timezone('US/Eastern')
        
        self.stdout.write(f"Fetching NFL schedule for {season_year}...")

        try:
            df = nfl.import_schedules([season_year])
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Failed to fetch schedule: {e}"))
            return

        self.stdout.write(f"Retrieved {len(df)} games.")
        self.stdout.write(f"Columns available: {list(df.columns)}")
        
        # Debug: Show sample of game times to understand format
        if not df.empty and 'gametime' in df.columns:
            sample_times = df['gametime'].dropna().head(5).tolist()
            self.stdout.write(f"Sample game times: {sample_times}")

        for _, row in df.iterrows():
            try:
                game_day_str = row.get('gameday')
                game_time_str = row.get('gametime')

                if not game_day_str:
                    skipped += 1
                    continue

                # Parse date part
                try:
                    date_part = parser.parse(str(game_day_str)).date()
                except (ValueError, TypeError) as e:
                    self.stdout.write(
                        self.style.WARNING(f"Could not parse date '{game_day_str}': {e}")
                    )
                    skipped += 1
                    continue

                # Parse time part with improved handling
                time_part = self.parse_game_time(game_time_str)

                # Combine date and time
                dt = datetime.combine(date_part, time_part)

                # Make timezone-aware using Eastern timezone
                start_time = eastern.localize(dt)

                # Convert to UTC for storage
                start_time_utc = start_time.astimezone(pytz.UTC)

                # Create a more robust external_id
                game_id = row.get('game_id')
                if not game_id:
                    game_id = f"{row.get('away_team', 'UNK')}@{row.get('home_team', 'UNK')}@{date_part.isoformat()}"

                game, created_flag = Game.objects.update_or_create(
                    external_id=game_id,
                    defaults={
                        'home_team': row.get('home_team', ''),
                        'away_team': row.get('away_team', ''),
                        'start_time': start_time_utc,
                        'sport': 'NFL',
                        'game_week': row.get('week', 0),
                        'location': row.get('location', ''),
                        'status': 'scheduled',
                        'season': row.get('season', season_year),
                        'game_type': row.get('game_type', 'REG'),  # REG, WC, DIV, CON, SB
                    }
                )
                
                if created_flag:
                    created += 1
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"Created: {game} at {start_time.strftime('%Y-%m-%d %I:%M %p %Z')} "
                            f"(Week {row.get('week', 'N/A')})"
                        )
                    )
                else:
                    updated += 1
                    self.stdout.write(
                        self.style.WARNING(
                            f"Updated: {game} at {start_time.strftime('%Y-%m-%d %I:%M %p %Z')} "
                            f"(Week {row.get('week', 'N/A')})"
                        )
                    )

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"Error processing row: {e}")
                )
                skipped += 1
                continue

        self.stdout.write(
            self.style.SUCCESS(
                f"Done! Created: {created}, Updated: {updated}, Skipped: {skipped}"
            )
        )
        
        # Summary of primetime games (games after 8 PM ET)
        # Note: This is approximate since we're checking UTC times
        primetime_games = Game.objects.filter(
            sport='NFL',
            start_time__date__gte=datetime(season_year, 8, 1).date(),
            start_time__date__lte=datetime(season_year + 1, 2, 28).date(),
        ).count()
        
        # Count games that match the primetime property
        total_games = Game.objects.filter(sport='NFL').count()
        actual_primetime = sum(1 for game in Game.objects.filter(sport='NFL') if game.is_primetime)
        
        self.stdout.write(
            self.style.SUCCESS(
                f"Total NFL games: {total_games}, "
                f"Primetime games (8 PM+ ET): {actual_primetime}"
            )
        )