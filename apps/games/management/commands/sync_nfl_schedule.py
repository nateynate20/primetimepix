from django.core.management.base import BaseCommand
from django.utils import timezone
import requests
from apps.games.models import Game
import pytz
import pandas as pd

class Command(BaseCommand):
    help = 'Sync NFL schedule using ESPN API with proper timezone handling'

    def handle(self, *args, **options):
        season = 2025
        self.stdout.write(f"Fetching NFL schedule for {season} via ESPN API...")

        urls = [
            (f"https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard?seasontype=2&dates={season}&limit=1000", 'regular'),
            (f"https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard?seasontype=3&dates={season}&limit=1000", 'playoff'),
        ]

        created, updated = 0, 0

        for url, default_type in urls:
            self.stdout.write(f"Fetching {default_type} season games...")
            response = requests.get(url, headers={"Accept": "application/json"})
            if response.status_code != 200:
                self.stdout.write(self.style.ERROR(f"Failed to fetch {default_type} games"))
                continue

            data = response.json()
            events = data.get('events', [])
            for ev in events:
                result = self._process_event(ev, season, default_type)
                if result == 'created':
                    created += 1
                elif result == 'updated':
                    updated += 1

        self.stdout.write(
            self.style.SUCCESS(f"Successfully synced {season} schedule. Created: {created}, Updated: {updated}")
        )

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

            home_score = int(home_team_data.get('score', 0)) if home_team_data.get('score') else None
            away_score = int(away_team_data.get('score', 0)) if away_team_data.get('score') else None

            status_detail = comp.get('status', {}).get('type', {})
            status = status_detail.get('description', 'Scheduled').lower()
            if status in ['final', 'final/ot', 'final overtime']:
                status = 'final'
            elif status in ['in progress', 'halftime']:
                status = 'in_progress'
            elif status in ['scheduled', 'pregame']:
                status = 'scheduled'

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
            print(f"Error processing event: {e}")
            return None
