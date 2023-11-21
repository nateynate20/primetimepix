# nfl_schedule/views.py
import csv
import os
from django.conf import settings
from django.shortcuts import render
from nfl_schedule.models import NFLGame

# ... (other imports)

# Function to read NFL game data from a CSV file
def read_nfl_game_data_from_csv(file_name):
    nfl_schedule = []

    file_path = os.path.join(settings.BASE_DIR, file_name)

    with open(file_path, 'r') as csv_file:
        csv_reader = csv.DictReader(csv_file)

        for row in csv_reader:
            week = row["Week"]
            home_team = row["Home"]
            away_team = row["Away"]
            start_time = row["Time"]
            date = row["Date"]
            nfl_schedule.append({
                'week': week,
                'home_team': home_team,
                'away_team': away_team,
                'start_time': start_time,
                'date': date,
            })

    return nfl_schedule

def import_nfl_schedule(request):
    file_name = 'NFL2023GMS.csv'
    csv_file_path = os.path.join(settings.BASE_DIR, file_name)

    nfl_schedule = read_nfl_game_data_from_csv(csv_file_path)

    if nfl_schedule:
        # Clear existing games before importing new ones
        NFLGame.objects.all().delete()

        # Save each game to the database
        for game_data in nfl_schedule:
                    
            NFLGame.objects.create(
                week=game_data['week'],
                date=game_data['date'],
                home_team=game_data['home_team'],
                away_team=game_data['away_team'],
                start_time=game_data['start_time'],
                )
            

        return render(request, 'nflpix/success_page.html', {'message': 'Data imported successfully'})
    else:
        error_message = "Failed to import NFL schedule data from the CSV file. Please try again later."
        return render(request, 'nflpix/error_page.html', {'error_message': error_message})
