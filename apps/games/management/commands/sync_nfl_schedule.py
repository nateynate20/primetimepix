import requests
from django.core.management.base import BaseCommand
from apps.games.models import Game
from datetime import datetime
from dateutil import parser

API_URL = "https://www.thesportsdb.com/api/v1/json/123/eventsseason.php?id=4391&s=2025"

class Command(BaseCommand):
    help = "Fetch and sync NFL schedule from TheSportsDB API"

    def handle(self, *args, **options):
        self.stdout.write(f"Fetching NFL schedule from {API_URL}...")

        response = requests.get(API_URL)
        if response.status_code != 200:
            self.stderr.write(f"Failed to fetch data. Status code: {response.status_code}")
            return

        data = response.json()
        events = data.get("events", [])

        if not events:
            self.stderr.write("No events found in API response.")
            return

        created_count = 0
        updated_count = 0

        for event in events:
            try:
                home_team = event.get("strHomeTeam")
                away_team = event.get("strAwayTeam")
                start_time_str = event.get("dateEvent") + " " + (event.get("strTime") or "00:00:00")

                # Parse datetime from string
                start_time = parser.parse(start_time_str)

                # Optional fields
                game_week = int(event.get("intRound") or 0)
                location = event.get("strVenue")
                external_id = event.get("idEvent")

                # Logos may be missing
                home_logo = event.get("strHomeTeamBadge")
                away_logo = event.get("strAwayTeamBadge")

                game, created = Game.objects.update_or_create(
                    home_team=home_team,
                    away_team=away_team,
                    start_time=start_time,
                    defaults={
                        "sport": "NFL",
                        "game_week": game_week,
                        "location": location,
                        "external_id": external_id,
                        "home_logo": home_logo,
                        "away_logo": away_logo,
                        "status": "scheduled",
                    }
                )

                if created:
                    created_count += 1
                    self.stdout.write(self.style.SUCCESS(f"Created: {game}"))
                else:
                    updated_count += 1
                    self.stdout.write(self.style.WARNING(f"Updated: {game}"))

            except Exception as e:
                self.stderr.write(self.style.ERROR(f"Failed to process event: {event.get('strEvent')}"))
                self.stderr.write(self.style.ERROR(str(e)))

        self.stdout.write(self.style.SUCCESS(f"✅ Done. Created: {created_count}, Updated: {updated_count}"))
