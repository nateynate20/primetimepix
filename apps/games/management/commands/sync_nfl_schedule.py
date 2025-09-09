from django.core.management.base import BaseCommand
from django.utils import timezone
import requests
from apps.games.models import Game
import pytz
import pandas as pd
from datetime import datetime, timedelta

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

    def handle(self, *args, **options):
        season = 2025
        current_week = options.get('week')
        all_weeks = options.get('all_weeks', False)
        
        self.stdout.write(f"Fetching NFL schedule for {season} via ESPN API...")

        if all_weeks:
            # Fetch entire season schedule first
            self._sync_season_schedule(season)
        
        if current_week:
            # Sync specific week
            self._sync_week_scores(season, current_week)
        else:
            # Sync current week and recent weeks with scores
            self._sync_recent_scores(season)

    def _sync_season_schedule(self, season):
        """Sync the full season schedule"""
        self.stdout.write("Syncing full season schedule...")
        
        urls = [
            (f"https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard?seasontype=2&dates={season}&limit=1000", 'regular'),
            (f"https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard?seasontype=3&dates={season}&limit=1000", 'playoff'),
        ]

        created, updated = 0, 0
        for url, default_type in urls:
            self.stdout.write(f"Fetching {default_type} season games...")
            response = requests.get(url, headers={"Accept": "application/json"})
            if response.status_code == 200:
                data = response.json()
                events = data.get('events', [])
                for ev in events:
                    result = self._process_event(ev, season, default_type)
                    if result == 'created':
                        created += 1
                    elif result == 'updated':
                        updated += 1
        
        self.stdout.write(f"Season schedule sync complete. Created: {created}, Updated: {updated}")

    def _sync_recent_scores(self, season):
        """Sync scores for recent weeks"""
        self.stdout.write("Syncing recent scores...")
        
        # Get current date range (last 10 days to next 3 days)
        today = datetime.now()
        start_date = today - timedelta(days=10)
        end_date = today + timedelta(days=3)
        
        date_range = []
        current_date = start_date
        while current_date <= end_date:
            date_range.append(current_date.strftime('%Y%m%d'))
            current_date += timedelta(days=1)
        
        created, updated = 0, 0
        
        for date_str in date_range:
            # Regular season
            url = f"https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard?seasontype=2&dates={date_str}"
            result_counts = self._fetch_and_process(url, season, 'regular')
            created += result_counts[0]
            updated += result_counts[1]
            
            # Playoffs (if applicable)
            url = f"https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard?seasontype=3&dates={date_str}"
            result_counts = self._fetch_and_process(url, season, 'playoff')
            created += result_counts[0]
            updated += result_counts[1]
        
        self.stdout.write(f"Recent scores sync complete. Created: {created}, Updated: {updated}")

    def _sync_week_scores(self, season, week):
        """Sync scores for a specific week"""
        self.stdout.write(f"Syncing week {week} scores...")
        
        urls = [
            (f"https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard?seasontype=2&week={week}&dates={season}", 'regular'),
            (f"https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard?seasontype=3&week={week}&dates={season}", 'playoff'),
        ]
        
        created, updated = 0, 0
        for url, default_type in urls:
            result_counts = self._fetch_and_process(url, season, default_type)
            created += result_counts[0]
            updated += result_counts[1]
        
        self.stdout.write(f"Week {week} sync complete. Created: {created}, Updated: {updated}")

    def _fetch_and_process(self, url, season, default_type):
        """Helper method to fetch and process games from a URL"""
        created, updated = 0, 0
        
        try:
            response = requests.get(url, headers={"Accept": "application/json"})
            if response.status_code == 200:
                data = response.json()
                events = data.get('events', [])
                
                for ev in events:
                    result = self._process_event(ev, season, default_type)
                    if result == 'created':
                        created += 1
                    elif result == 'updated':
                        updated += 1
            else:
                self.stdout.write(f"Failed to fetch from {url} - Status: {response.status_code}")
        except Exception as e:
            self.stdout.write(f"Error fetching from {url}: {e}")
        
        return created, updated

    def _process_event(self, event, season, default_game_type):
        try:
            comp = event.get('competitions', [{}])[0]
            game_id = event.get('id')
            date_str = comp.get('date')
            if not date_str:
                return None

            start_utc = pd.to_datetime(date_str)
            if start_utc.tzinfo is None:
                start_utc = pytz.UTC.localize(start_utc)

            season_info = event.get('season', {})
            season_type = season_info.get('type', 2)
            week = event.get('week', {}).get('number', 0)

            game_type_map = {1: 'preseason', 2: 'regular', 3: 'playoff', 4: 'playoff'}
            game_type = game_type_map.get(season_type, default_game_type)

            if game_type == 'playoff':
                name = event.get('name', '').lower()
                if 'super bowl' in name:
                    game_type = 'superbowl'
                elif 'wild card' in name:
                    game_type = 'wildcard'
                elif 'divisional' in name:
                    game_type = 'divisional'
                elif 'conference' in name:
                    game_type = 'conference'

            competitors = comp.get('competitors', [])
            if len(competitors) < 2:
                return None

            home_team_data = next((c for c in competitors if c.get('homeAway') == 'home'), competitors[0])
            away_team_data = next((c for c in competitors if c.get('homeAway') == 'away'), competitors[1])

            home_team = home_team_data.get('team', {}).get('displayName', '')
            away_team = away_team_data.get('team', {}).get('displayName', '')

            # Better score handling - check if score exists and is not empty string
            home_score = None
            away_score = None
            
            if home_team_data.get('score') and str(home_team_data.get('score')).strip():
                try:
                    home_score = int(home_team_data.get('score'))
                except (ValueError, TypeError):
                    pass
                    
            if away_team_data.get('score') and str(away_team_data.get('score')).strip():
                try:
                    away_score = int(away_team_data.get('score'))
                except (ValueError, TypeError):
                    pass

            status_detail = comp.get('status', {}).get('type', {})
            status = status_detail.get('description', 'Scheduled').lower()
            if status in ['final', 'final/ot', 'final overtime']:
                status = 'final'
            elif status in ['in progress', 'halftime', '1st quarter', '2nd quarter', '3rd quarter', '4th quarter']:
                status = 'in_progress'
            elif status in ['scheduled', 'pregame']:
                status = 'scheduled'

            # Debug output for games with scores
            if home_score is not None or away_score is not None:
                self.stdout.write(f"Found scores: {away_team} {away_score} - {home_score} {home_team} ({status})")

            obj, was_created = Game.objects.update_or_create(
                game_id=game_id,
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

            return 'created' if was_created else 'updated'
        except Exception as e:
            self.stdout.write(f"Error processing event: {e}")
            return None