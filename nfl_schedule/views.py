#nfl_schedule/views.py
import csv
import os # Add this import
from django.conf import settings
from django.shortcuts import render
from nfl_schedule.models import NFLGame


# Function to read NFL game data from a CSV file
def read_nfl_game_data_from_csv(file_name):
    nfl_schedule = []

    # Construct the full file path using BASE_DIR
    file_path = os.path.join(settings.BASE_DIR, file_name)

    with open(file_path, 'r') as csv_file:
        csv_reader = csv.DictReader(csv_file)
        
        for row in csv_reader:
            week = row["Week"]
            home_team = row["Home"]
            away_team = row["Away"]
            start_time = f"{row['Date']} {row['Time']}"
            nfl_schedule.append({
                'week': week,
                'home_team': home_team,
                'away_team': away_team,
                'start_time': start_time,
            })

    return nfl_schedule


def import_nfl_schedule(request):
    file_name = 'NFL2023GMS.csv'  # Name of your CSV file
    csv_file_path = os.path.join(settings.BASE_DIR, file_name)

    nfl_schedule = read_nfl_game_data_from_csv(csv_file_path)

    if nfl_schedule:
        # If data is successfully saved, you can redirect to a success page or render a success message
        return render(request, 'nflpix/success_page.html', {'message': 'Data imported successfully'})
    else:
        error_message = "Failed to import NFL schedule data from the CSV file. Please try again later."
        return render(request, 'nflpix/error_page.html', {'error_message': error_message})

