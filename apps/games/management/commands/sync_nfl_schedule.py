from django.core.management.base import BaseCommand
from django.utils import timezone
import requests
import pandas as pd
from apps.games.models import Game
import pytz

class Command(BaseCommand):
    help = 'Sync NFL schedule using ESPN API'

    def handle(self, *args, **options):
        season = 2025
        self.stdout.write(f"Fetching NFL schedule for {season} via ESPN API...")

        url = (
            "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard"
            f"?seasontype=2&dates={season}&limit=1000"
        )

        response = requests.get(url, headers={"Accept": "application/json"})
        data = response.json()

        events = data.get('events', [])
        created, updated = 0, 0

        eastern = pytz.timezone('US/Eastern')

        for ev in events:
            comp = ev.get('competitions', [{}])[0]
            game_id = ev.get('id')
            start_utc = pd.to_datetime(comp.get('date'))
            if start_utc.tzinfo is None:
                start_utc = start_utc.tz_localize('UTC')

            season_type = comp.get('season', {}).get('type')
            week = comp.get('week')
            game_type = {1: 'preseason', 2: 'regular', 3: 'playoff'}.get(season_type, 'unknown')

            home = comp.get('competitors', [])[0].get('team', {}).get('shortDisplayName')
            away = comp.get('competitors', [])[1].get('team', {}).get('shortDisplayName')

            obj, was_created = Game.objects.update_or_create(
                game_id=game_id,
                defaults={
                    'season': season,
                    'week': week or 0,
                    'game_type': game_type,
                    'start_time': start_utc,
                    'home_team': home,
                    'away_team': away,
                    'status': comp.get('status', {}).get('type', {}).get('description', 'scheduled')
                }
            )
            created += was_created
            updated += (not was_created)
            self.stdout.write(f"{'Created' if was_created else 'Updated'}: {away} @ {home}")

        self.stdout.write(
            self.style.SUCCESS(f"Successfully synced. Created: {created}, Updated: {updated}")
        )
