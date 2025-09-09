from django.core.management.base import BaseCommand
from django.utils import timezone
import requests
from apps.games.models import Game
import pytz
from datetime import datetime, timedelta
import time

class Command(BaseCommand):
    help = 'Sync NFL schedule using ESPN API with proper timezone handling'

    def add_arguments(self, parser):
        parser.add_argument(
            '--week',
            type=int,
            help='Specific week to sync (optional)',
        )
        parser.add_argument(
            '--all-weeks',
            action='store_true',
            help='Sync all weeks for the season',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be synced without saving to database',
        )
        parser.add_argument(
            '--season',
            type=int,
            default=2025,
            help='Season year (default: 2025)',
        )

    def handle(self, *args, **options):
        season = options.get('season', 2025)
        current_week = options.get('week')
        all_weeks = options.get('all_weeks', False)
        dry_run = options.get('dry_run', False)
        
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN MODE - No changes will be saved"))
        
        self.stdout.write(f"Fetching NFL schedule for {season} via ESPN API...")

        if all_weeks:
            self._sync_season_schedule(season, dry_run)
        
        if current_week:
            self._sync_week_scores(season, current_week, dry_run)
        else:
            self._sync_recent_scores(season, dry_run)

    def _sync_season_schedule(self, season, dry_run=False):
        """Sync the full season schedule"""
        self.stdout.write("Syncing full season schedule...")
        
        # Use week-by-week approach for better reliability
        created, updated = 0, 0
        for week in range(1, 19):  # NFL regular season weeks 1-18
            self.stdout.write(f"Fetching week {week}...")
            week_counts = self._sync_week_data(season, week, 'regular', dry_run)
            created += week_counts[0]
            updated += week_counts[1]
            time.sleep(0.5)  # Rate limiting
        
        # Sync playoffs
        for week in range(1, 5):  # Playoff weeks
            self.stdout.write(f"Fetching playoff week {week}...")
            week_counts = self._sync_week_data(season, week, 'playoff', dry_run)
            created += week_counts[0] 
            updated += week_counts[1]
            time.sleep(0.5)
        
        self.stdout.write(f"Season schedule sync complete. Created: {created}, Updated: {updated}")

    def _sync_recent_scores(self, season, dry_run=False):
        """Sync scores for recent weeks"""
        self.stdout.write("Syncing recent scores...")
        
        # Get current date range (last 7 days to next 7 days)
        today = datetime.now()
        start_date = today - timedelta(days=7)
        end_date = today + timedelta(days=7)
        
        created, updated = 0, 0
        
        current_date = start_date
        while current_date <= end_date:
            date_str = current_date.strftime('%Y%m%d')
            self.stdout.write(f"Fetching games for {current_date.strftime('%Y-%m-%d')}...")
            
            # Regular season
            url = f"https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard?seasontype=2&dates={date_str}"
            result_counts = self._fetch_and_process(url, season, 'regular', dry_run)
            created += result_counts[0]
            updated += result_counts[1]
            
            # Playoffs
            url = f"https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard?seasontype=3&dates={date_str}"
            result_counts = self._fetch_and_process(url, season, 'playoff', dry_run)
            created += result_counts[0]
            updated += result_counts[1]
            
            current_date += timedelta(days=1)
            time.sleep(0.3)  # Rate limiting
        
        self.stdout.write(f"Recent scores sync complete. Created: {created}, Updated: {updated}")

    def _sync_week_scores(self, season, week, dry_run=False):
        """Sync scores for a specific week"""
        self.stdout.write(f"Syncing week {week} scores...")
        
        created, updated = 0, 0
        
        # Regular season
        result_counts = self._sync_week_data(season, week, 'regular', dry_run)
        created += result_counts[0]
        updated += result_counts[1]
        
        # Playoffs (if week number makes sense for playoffs)
        if week <= 4:
            result_counts = self._sync_week_data(season, week, 'playoff', dry_run)
            created += result_counts[0]
            updated += result_counts[1]
        
        self.stdout.write(f"Week {week} sync complete. Created: {created}, Updated: {updated}")

    def _sync_week_data(self, season, week, season_type, dry_run=False):
        """Sync data for a specific week and season type"""
        season_type_num = 2 if season_type == 'regular' else 3
        url = f"https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard?seasontype={season_type_num}&week={week}&dates={season}"
        return self._fetch_and_process(url, season, season_type, dry_run)

    def _fetch_and_process(self, url, season, default_type, dry_run=False):
        """Helper method to fetch and process games from a URL"""
        created, updated = 0, 0
        
        try:
            response = requests.get(url, headers={
                "Accept": "application/json",
                "User-Agent": "NFL-Picks-App/1.0"
            }, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                events = data.get('events', [])
                
                if not events:
                    self.stdout.write(f"No events found at {url}")
                    return created, updated
                
                for ev in events:
                    result = self._process_event(ev, season, default_type, dry_run)
                    if result == 'created':
                        created += 1
                    elif result == 'updated':
                        updated += 1
            else:
                self.stdout.write(
                    self.style.WARNING(f"Failed to fetch from {url} - Status: {response.status_code}")
                )
        except requests.RequestException as e:
            self.stdout.write(
                self.style.ERROR(f"Network error fetching from {url}: {e}")
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Error fetching from {url}: {e}")
            )
        
        return created, updated

    def _process_event(self, event, season, default_game_type, dry_run=False):
        try:
            comp = event.get('competitions', [{}])[0]
            game_id = event.get('id')
            date_str = comp.get('date')
            
            if not date_str or not game_id:
                self.stdout.write(f"Missing essential data for event: {event.get('name', 'Unknown')}")
                return None

            # Parse the datetime - ESPN returns ISO format in UTC
            try:
                start_utc = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                if start_utc.tzinfo is None:
                    start_utc = pytz.UTC.localize(start_utc)
            except ValueError as e:
                self.stdout.write(f"Could not parse date '{date_str}': {e}")
                return None

            # Get season and week info
            season_info = event.get('season', {})
            season_type = season_info.get('type', 2)
            week = event.get('week', {}).get('number', 0)

            # Map season type to game type
            game_type_map = {1: 'preseason', 2: 'regular', 3: 'playoff', 4: 'playoff'}
            game_type = game_type_map.get(season_type, default_game_type)

            # Refine playoff game types
            if game_type == 'playoff':
                name = event.get('name', '').lower()
                if 'super bowl' in name:
                    game_type = 'superbowl'
                elif 'wild card' in name or 'wildcard' in name:
                    game_type = 'wildcard'
                elif 'divisional' in name:
                    game_type = 'divisional'
                elif 'conference' in name or 'championship' in name:
                    game_type = 'conference'

            # Get team information
            competitors = comp.get('competitors', [])
            if len(competitors) < 2:
                self.stdout.write(f"Not enough competitors for event: {event.get('name', 'Unknown')}")
                return None

            home_team_data = next((c for c in competitors if c.get('homeAway') == 'home'), None)
            away_team_data = next((c for c in competitors if c.get('homeAway') == 'away'), None)
            
            if not home_team_data or not away_team_data:
                # Fall back to position-based assignment
                home_team_data = competitors[0]
                away_team_data = competitors[1]

            home_team = home_team_data.get('team', {}).get('displayName', 'Unknown')
            away_team = away_team_data.get('team', {}).get('displayName', 'Unknown')

            # Parse scores with better error handling
            home_score = self._parse_score(home_team_data.get('score'))
            away_score = self._parse_score(away_team_data.get('score'))

            # Parse game status
            status_detail = comp.get('status', {}).get('type', {})
            status_name = status_detail.get('name', 'scheduled').lower()
            status_description = status_detail.get('description', 'Scheduled').lower()
            
            # Map ESPN statuses to our statuses
            if status_name in ['final'] or 'final' in status_description:
                status = 'final'
            elif status_name in ['in'] or any(x in status_description for x in ['progress', 'quarter', 'halftime', 'overtime']):
                status = 'in_progress'
            elif status_name in ['pre'] or 'scheduled' in status_description:
                status = 'scheduled'
            else:
                status = 'scheduled'  # Default fallback

            # Show what we're about to do
            eastern = pytz.timezone('US/Eastern')
            start_et = start_utc.astimezone(eastern)
            
            action = "Would create" if dry_run else "Processing"
            self.stdout.write(
                f"{action}: {away_team} @ {home_team} - "
                f"Week {week} - {start_et.strftime('%a %m/%d %I:%M %p ET')} - "
                f"Status: {status}"
            )
            
            if home_score is not None or away_score is not None:
                self.stdout.write(f"  Scores: {away_team} {away_score} - {home_score} {home_team}")

            if dry_run:
                return 'created'  # Simulate creation for dry run

            # Create or update the game
            obj, was_created = Game.objects.update_or_create(
                game_id=str(game_id),
                defaults={
                    'season': season,
                    'week': week,
                    'game_type': game_type,
                    'start_time': start_utc,
                    'home_team': home_team,
                    'away_team': away_team,
                    'home_score': home_score,
                    'away_score': away_score,
                    'status': status,
                }
            )

            if was_created:
                self.stdout.write(f"  ✓ Created game {obj.id}")
                return 'created'
            else:
                self.stdout.write(f"  ✓ Updated game {obj.id}")
                return 'updated'
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Error processing event {event.get('id', 'Unknown')}: {e}")
            )
            return None

    def _parse_score(self, score_value):
        """Safely parse score value to integer"""
        if score_value is None:
            return None
        
        # Handle string scores
        if isinstance(score_value, str):
            score_value = score_value.strip()
            if not score_value or score_value == '':
                return None
        
        try:
            return int(score_value)
        except (ValueError, TypeError):
            return None