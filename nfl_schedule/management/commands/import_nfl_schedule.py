import os
import csv
from django.conf import settings
from django.core.management.base import BaseCommand
from nfl_schedule.models import NFLGame
from nfl_schedule.views import read_nfl_game_data_from_csv 

class Command(BaseCommand):
    help = 'Import NFL schedule data from CSV file'

    def handle(self, *args, **options):
        file_name = 'NFL2023GMS.csv'
        file_path = os.path.join(settings.BASE_DIR, 'nfl_schedule', file_name)

        nfl_schedule = read_nfl_game_data_from_csv(file_path)

        if nfl_schedule:
            # Clear existing games before importing new ones
            NFLGame.objects.all().delete()

            # Save each game to the database
            for game_data in nfl_schedule:
                NFLGame.objects.create(
                    week=game_data['week'],
                    home_team=game_data['home_team'],
                    away_team=game_data['away_team'],
                    start_time=game_data['start_time'],
                )

            self.stdout.write(self.style.SUCCESS('Data imported successfully'))
        else:
            self.stderr.write(self.style.ERROR('Failed to import NFL schedule data from the CSV file.'))