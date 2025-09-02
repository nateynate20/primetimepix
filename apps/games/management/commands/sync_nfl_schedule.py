from django.core.management.base import BaseCommand
from django.utils import timezone
import nfl_data_py as nfl
import pandas as pd
from apps.games.models import Game

class Command(BaseCommand):
    help = 'Sync NFL schedule using nfl_data_py'

    def handle(self, *args, **options):
        current_year = timezone.now().year
        
        # Fetch schedule
        self.stdout.write("Fetching NFL schedule...")
        schedule = nfl.import_schedules([current_year])
        
        # Filter for future games and primetime slots
        schedule['start_time'] = pd.to_datetime(schedule['gameday'] + ' ' + schedule['gametime'])
        primetime_schedule = schedule[
            (schedule['start_time'] >= str(timezone.now())) & 
            (pd.to_datetime(schedule['gametime']).dt.hour >= 17)  # After 5 PM
        ]

        created, updated = 0, 0
        for _, game in primetime_schedule.iterrows():
            game_obj, was_created = Game.objects.update_or_create(
                game_id=str(game['game_id']),
                defaults={
                    'season': current_year,
                    'week': game['week'],
                    'game_type': game['game_type'],
                    'start_time': game['start_time'],
                    'home_team': game['home_team'],
                    'away_team': game['away_team'],
                    'status': 'scheduled'
                }
            )
            
            if was_created:
                created += 1
            else:
                updated += 1
                
            self.stdout.write(f"Synced: {game['away_team']} @ {game['home_team']}")

        self.stdout.write(
            self.style.SUCCESS(f'Successfully synced schedule. Created: {created}, Updated: {updated}')
        )
