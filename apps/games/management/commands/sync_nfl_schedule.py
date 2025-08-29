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

    # Team logo mapping - Fixed LA Rams issue
    TEAM_LOGOS = {
        'ARI': 'https://a.espncdn.com/i/teamlogos/nfl/500/ari.png',
        'ATL': 'https://a.espncdn.com/i/teamlogos/nfl/500/atl.png',
        'BAL': 'https://a.espncdn.com/i/teamlogos/nfl/500/bal.png',
        'BUF': 'https://a.espncdn.com/i/teamlogos/nfl/500/buf.png',
        'CAR': 'https://a.espncdn.com/i/teamlogos/nfl/500/car.png',
        'CHI': 'https://a.espncdn.com/i/teamlogos/nfl/500/chi.png',
        'CIN': 'https://a.espncdn.com/i/teamlogos/nfl/500/cin.png',
        'CLE': 'https://a.espncdn.com/i/teamlogos/nfl/500/cle.png',
        'DAL': 'https://a.espncdn.com/i/teamlogos/nfl/500/dal.png',
        'DEN': 'https://a.espncdn.com/i/teamlogos/nfl/500/den.png',
        'DET': 'https://a.espncdn.com/i/teamlogos/nfl/500/det.png',
        'GB': 'https://a.espncdn.com/i/teamlogos/nfl/500/gb.png',
        'HOU': 'https://a.espncdn.com/i/teamlogos/nfl/500/hou.png',
        'IND': 'https://a.espncdn.com/i/teamlogos/nfl/500/ind.png',
        'JAX': 'https://a.espncdn.com/i/teamlogos/nfl/500/jax.png',
        'KC': 'https://a.espncdn.com/i/teamlogos/nfl/500/kc.png',
        'LV': 'https://a.espncdn.com/i/teamlogos/nfl/500/lv.png',
        'LAC': 'https://a.espncdn.com/i/teamlogos/nfl/500/lac.png',
        # LA Rams - multiple possible abbreviations
        'LAR': 'https://a.espncdn.com/i/teamlogos/nfl/500/lar.png',
        'LA': 'https://a.espncdn.com/i/teamlogos/nfl/500/lar.png',  # Alternative
        'STL': 'https://a.espncdn.com/i/teamlogos/nfl/500/lar.png', # Legacy
        'MIA': 'https://a.espncdn.com/i/teamlogos/nfl/500/mia.png',
        'MIN': 'https://a.espncdn.com/i/teamlogos/nfl/500/min.png',
        'NE': 'https://a.espncdn.com/i/teamlogos/nfl/500/ne.png',
        'NO': 'https://a.espncdn.com/i/teamlogos/nfl/500/no.png',
        'NYG': 'https://a.espncdn.com/i/teamlogos/nfl/500/nyg.png',
        'NYJ': 'https://a.espncdn.com/i/teamlogos/nfl/500/nyj.png',
        'PHI': 'https://a.espncdn.com/i/teamlogos/nfl/500/phi.png',
        'PIT': 'https://a.espncdn.com/i/teamlogos/nfl/500/pit.png',
        'SF': 'https://a.espncdn.com/i/teamlogos/nfl/500/sf.png',
        'SEA': 'https://a.espncdn.com/i/teamlogos/nfl/500/sea.png',
        'TB': 'https://a.espncdn.com/i/teamlogos/nfl/500/tb.png',
        'TEN': 'https://a.espncdn.com/i/teamlogos/nfl/500/ten.png',
        'WAS': 'https://a.espncdn.com/i/teamlogos/nfl/500/was.png',
    }

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
        
        # Debug: Show sample of game times and team names to understand format
        if not df.empty:
            if 'gametime' in df.columns:
                sample_times = df['gametime'].dropna().head(5).tolist()
                self.stdout.write(f"Sample game times: {sample_times}")
            
            # Debug: Show unique team names to check Rams abbreviation
            home_teams = df['home_team'].dropna().unique()
            away_teams = df['away_team'].dropna().unique()
            all_teams = set(list(home_teams) + list(away_teams))
            rams_teams = [team for team in all_teams if 'ram' in team.lower() or 'la' in team.lower()]
            if rams_teams:
                self.stdout.write(f"Rams-related team names found: {rams_teams}")

        for _, row in df.iterrows():
            try:
                game_day_str = row.get('gameday')
                game_time_str = row.get('gametime')
                home_team = row.get('home_team', '')
                away_team = row.get('away_team', '')

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
                    game_id = f"{away_team}@{home_team}@{date_part.isoformat()}"

                game, created_flag = Game.objects.update_or_create(
                    external_id=game_id,
                    defaults={
                        'home_team': home_team,
                        'away_team': away_team,
                        'start_time': start_time_utc,
                        'sport': 'NFL',
                        'game_week': row.get('week', 0),
                        'location': row.get('location', ''),
                        'status': 'scheduled',
                        'season': row.get('season', season_year),
                        'game_type': row.get('game_type', 'REG'),  # REG, WC, DIV, CON, SB
                        # Add logo URLs with debug info
                        'home_logo': self.TEAM_LOGOS.get(home_team, ''),
                        'away_logo': self.TEAM_LOGOS.get(away_team, ''),
                    }
                )
                
                # Debug missing logos
                if not self.TEAM_LOGOS.get(home_team) or not self.TEAM_LOGOS.get(away_team):
                    missing_teams = []
                    if not self.TEAM_LOGOS.get(home_team):
                        missing_teams.append(f"Home: {home_team}")
                    if not self.TEAM_LOGOS.get(away_team):
                        missing_teams.append(f"Away: {away_team}")
                    self.stdout.write(
                        self.style.WARNING(f"Missing logo mapping for: {', '.join(missing_teams)}")
                    )
                
                if created_flag:
                    created += 1
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"Created: {game} at {start_time.strftime('%Y-%m-%d %I:%M %p %Z')} "
                            f"(Week {row.get('week', 'N/A')}) - Primetime: {game.is_primetime}"
                        )
                    )
                else:
                    updated += 1
                    self.stdout.write(
                        self.style.WARNING(
                            f"Updated: {game} at {start_time.strftime('%Y-%m-%d %I:%M %p %Z')} "
                            f"(Week {row.get('week', 'N/A')}) - Primetime: {game.is_primetime}"
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
        
        # Summary of primetime games
        total_games = Game.objects.filter(sport='NFL').count()
        actual_primetime = sum(1 for game in Game.objects.filter(sport='NFL') if game.is_primetime)
        
        self.stdout.write(
            self.style.SUCCESS(
                f"Total NFL games: {total_games}, "
                f"Primetime games (8 PM+ ET): {actual_primetime}"
            )
        )