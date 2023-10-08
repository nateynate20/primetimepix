from django.shortcuts import render
import requests
from bs4 import BeautifulSoup
from .models import NFLGame

# Function to scrape NFL schedule data from pro-football-reference.com
def scrape_nfl_schedule(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        nfl_schedule = {}
        current_week = None

        # Find the elements containing schedule data
        schedule_tables = soup.find_all('table', class_='suppress_glossary')
        for table in schedule_tables:
            week_header = table.find_previous('h2')
            if week_header:
                current_week = week_header.text.strip()
                nfl_schedule[current_week] = []

            rows = table.find_all('tr')
            for row in rows[1:]:  # Skip the header row
                columns = row.find_all(['th', 'td'])
                if len(columns) >= 4:
                    home_team = columns[1].text.strip()
                    away_team = columns[2].text.strip()
                    start_time = columns[3].text.strip()
                    nfl_schedule[current_week].append({
                        'home_team': home_team,
                        'away_team': away_team,
                        'start_time': start_time
                    })

        return nfl_schedule
    except requests.exceptions.RequestException as e:
        print(f"Error fetching NFL schedule data: {e}")
        return None

# Function to save scraped NFL schedule data to the database
def save_nfl_schedule_to_db(schedule):
    for week, games in schedule.items():
        for game in games:
            nfl_game = NFLGame(
                week=week,
                home_team=game['home_team'],
                away_team=game['away_team'],
                start_time=game['start_time']
            )
            nfl_game.save()

# Django view to scrape and display NFL schedule
def display_nfl_schedule(request):
    pfr_url = "https://www.pro-football-reference.com/years/2023/games.htm"  # Update the URL for the desired year
    nfl_schedule = scrape_nfl_schedule(pfr_url)

    if nfl_schedule:
        save_nfl_schedule_to_db(nfl_schedule)
        games = NFLGame.objects.filter(week="Week 5")  # Change "Week 2" to the desired week
        return render(request, 'nfl_schedule/schedule.html', {'games': games})
        
    else:
        error_message = "Failed to fetch NFL schedule data."
        
        return render(request, 'nfl_schedule/error.html', {'error_message': error_message})
        

# Create your views here.
