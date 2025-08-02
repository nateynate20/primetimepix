import requests
from datetime import datetime
from django.core.management.base import BaseCommand
from django.conf import settings
from nfl_schedule.models import NFLGame

class Command(BaseCommand):
    help = 'Sync NFL schedule and scores from TheSportsDB API'

    def safe_int(self, value):
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    def handle(self, *args, **kwargs):
        league_id = '4391'  # NFL league ID on TheSportsDB
        season = '2025'     # Update season as needed
        api_key = settings.THESPORTSDB_API_KEY

        url = f'https://www.thesportsdb.com/api/v1/json/{api_key}/eventsseason.php?id={league_id}&s={season}'
        self.stdout.write(f"Fetching NFL schedule from {url}...")

        try:
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
            events = data.get('events', [])

            if not events:
                self.stdout.write(self.style.WARNING("No events found from API."))
                return

            for event in events:
                event_id = event.get('idEvent')
                if not event_id:
                    self.stdout.write(self.style.WARNING("Skipping event without event_id"))
                    continue

                # Parse date
                event_date = event.get('dateEvent')
                try:
                    date_obj = datetime.strptime(event_date, '%Y-%m-%d').date() if event_date else None
                except ValueError:
                    self.stdout.write(self.style.WARNING(f"Skipping event with invalid date format: {event_id}"))
                    continue

                # Parse time (some times may be null or empty)
                event_time = event.get('strTime')
                try:
                    time_obj = datetime.strptime(event_time, '%H:%M:%S').time() if event_time else None
                except ValueError:
                    time_obj = None

                # Extract week (sometimes available as 'intRound' or 'strRound')
                week = event.get('intRound') or event.get('strRound') or None
                if week is not None:
                    week = str(week)

                # Extract logos for home and away teams if available
                home_logo = event.get('strHomeTeamBadge') or ''
                away_logo = event.get('strAwayTeamBadge') or ''

                # Extract scores, convert to int or None if not present
                home_score = self.safe_int(event.get('intHomeScore'))
                away_score = self.safe_int(event.get('intAwayScore'))

                status = event.get('strStatus') or 'Scheduled'

                # Update or create the game in the DB
                game, created = NFLGame.objects.update_or_create(
                    event_id=event_id,
                    defaults={
                        'week': week,
                        'date': date_obj,
                        'start_time': time_obj,
                        'home_team': event.get('strHomeTeam', ''),
                        'away_team': event.get('strAwayTeam', ''),
                        'home_logo': home_logo,
                        'away_logo': away_logo,
                        'home_score': home_score,
                        'away_score': away_score,
                        'status': status,
                    }
                )
                action = "Created" if created else "Updated"
                self.stdout.write(f"{action} game: {game}")

            self.stdout.write(self.style.SUCCESS("NFL schedule sync completed successfully."))

        except requests.RequestException as e:
            self.stderr.write(self.style.ERROR(f"Error fetching NFL schedule: {e}"))
