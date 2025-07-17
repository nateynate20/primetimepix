import os
import csv
from django.conf import settings
from django.core.management.base import BaseCommand
from nfl_schedule.models import NFLGame

class Command(BaseCommand):
    help = 'Import NFL schedule data from CSV file'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            default='NFL2023GMS.csv',
            help='CSV file name to import (default: NFL2023GMS.csv)'
        )

    def handle(self, *args, **options):
        file_name = options['file']
        file_path = os.path.join(settings.BASE_DIR, 'nfl_schedule', file_name)

        if not os.path.exists(file_path):
            self.stderr.write(self.style.ERROR(f'CSV file not found at {file_path}'))
            return

        with open(file_path, 'r') as csv_file:
            csv_reader = csv.DictReader(csv_file)
            nfl_schedule = []
            for row in csv_reader:
                nfl_schedule.append({
                    'week': row.get('Week', ''),
                    'home_team': row.get('Home', ''),
                    'away_team': row.get('Away', ''),
                    'start_time': row.get('Time', ''),
                    'date': row.get('Date', ''),
                })

        if nfl_schedule:
            NFLGame.objects.all().delete()  # Clear existing games

            for game_data in nfl_schedule:
                NFLGame.objects.create(
                    week=game_data['week'],
                    date=game_data['date'],
                    home_team=game_data['home_team'],
                    away_team=game_data['away_team'],
                    start_time=game_data['start_time'],
                    home_score=0,
                    away_score=0,
                    status='Scheduled'
                )

            self.stdout.write(self.style.SUCCESS('NFL schedule imported successfully.'))
        else:
            self.stderr.write(self.style.ERROR('No data found in CSV file.'))
