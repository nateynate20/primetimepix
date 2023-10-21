# views.py

from django.shortcuts import render
import requests
from bs4 import BeautifulSoup
from .models import NFLGame
from datetime import datetime

# Function to scrape NFL schedule data from pro-football-reference.com
def scrape_nfl_schedule(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.61 Safari/537.36"
    }
    try:
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')

            nfl_schedule = []

            # Find the table containing the schedule data
            schedule_table = soup.find('table', {'id': 'games'})
            if schedule_table:
                rows = schedule_table.find_all('tr')
                for row in rows[1:]:  # Skip the header row
                    columns = row.find_all(['th', 'td'])
                    if len(columns) >= 3:  # Check if there are at least 3 columns in the row
                        week = columns[0].text.strip()
                        date = columns[1].text.strip()
                        winner = columns[2].text.strip()
                        loser = columns[3].text.strip()

                        # Modify the date format to 'MM/DD/YYYY'
                        date = date.strip()

                        # Add this data to the nfl_schedule dictionary
                        nfl_schedule.append({
                            'week': week,
                            'home_team': winner,
                            'away_team': loser,
                            'date': date
                        })

            return nfl_schedule
        else:
            return None
    except requests.exceptions.RequestException as e:
        # Handle network or request-related errors
        print("Error:", e)
        return None

# Function to determine the current NFL week
def get_current_nfl_week(nfl_schedule):
    # Get the current date
    current_date = datetime.now().date()

    for game in nfl_schedule:
        try:
            game_date = datetime.strptime(game['date'], "%a, %m/%d/%Y").date()
        except ValueError:
            game_date = datetime(2023, 1, 1).date()  # Use a suitable default date

        if game_date >= current_date:
            # The first game with a date on or after the current date
            return game['week']

    # If no future games were found, assume the season has ended
    return "Regular Season Ended"

# Function to filter primetime games for the current NFL week
def get_primetime_games(schedule, current_week):
    primetime_slots = ["Sunday Night", "Monday Night", "Thursday Night"]

    primetime_games = []

    for game in schedule:
        if game['week'] == current_week:
            # Check if the game's start time is in a primetime slot
            if any(slot in game['start_time'] for slot in primetime_slots):
                primetime_games.append(game)

    return primetime_games

# Function to save NFL schedule data to the database
def save_nfl_schedule_to_db(nfl_schedule):
    for game in nfl_schedule:
        # Create an NFLGame object and save it to the database
        nfl_game = NFLGame(
            week=game['week'],
            home_team=game['home_team'],
            away_team=game['away_team'],
            date=game['date'],
        )
        nfl_game.save()

# Django view to scrape and display NFL schedule
def display_nfl_schedule(request):
    pfr_url = "https://www.pro-football-reference.com/years/2023/games.htm"  # URL for the 2023 NFL schedule
    nfl_schedule = scrape_nfl_schedule(pfr_url)

    if nfl_schedule:
        current_week = get_current_nfl_week(nfl_schedule)

        if current_week == "Regular Season Ended":
            error_message = "The regular season has ended. No upcoming games."
            return render(request, 'nfl_schedule/schedule.html', {'error_message': error_message})

        primetime_games = get_primetime_games(nfl_schedule, current_week)

        # Save the scraped data to the database
        save_nfl_schedule_to_db(nfl_schedule)

        return render(request, 'nfl_schedule/schedule.html', {'games': primetime_games})
    else:
        error_message = "Failed to fetch NFL schedule data. Please try again later."
        return render(request, 'nfl_schedule/schedule.html', {'error_message': error_message})
