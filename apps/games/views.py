from datetime import datetime, date, timedelta, time
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from apps.games.models import Game


def get_thanksgiving_date(year):
    nov1 = date(year, 11, 1)
    first_thursday = nov1 + timedelta(days=(3 - nov1.weekday()) % 7)
    return first_thursday + timedelta(weeks=3)


@login_required(login_url='login')
def view_schedule_page(request):
    selected_team = request.GET.get('team', '').strip()

    today = date.today()
    now = datetime.now()
    year = today.year
    PRIMETIME_TIME = time(20, 0)

    holiday_dates = [
        get_thanksgiving_date(year),
        date(year, 12, 25),
        date(year + 1 if today.month == 12 else year, 1, 1),
    ]

    upcoming_games = Game.objects.filter(start_time__gte=now)

    # Fetch separately as lists
    primetime_games = list(upcoming_games.filter(start_time__time__gte=PRIMETIME_TIME))
    holiday_games = list(upcoming_games.filter(start_time__date__in=holiday_dates))

    combined_games = primetime_games + holiday_games

    # Remove duplicates by game id
    seen_ids = set()
    unique_games = []
    for game in combined_games:
        if game.id not in seen_ids:
            unique_games.append(game)
            seen_ids.add(game.id)

    # Filter by selected team
    if selected_team:
        unique_games = [
            g for g in unique_games
            if selected_team.lower() in g.home_team.lower() or selected_team.lower() in g.away_team.lower()
        ]

    # Sort in Python
    unique_games.sort(key=lambda g: (g.start_time.date(), g.start_time.time()))

    # Teams list for filter dropdown
    teams = Game.objects.values_list('home_team', flat=True).distinct().order_by('home_team')

    # Paginate
    paginator = Paginator(unique_games, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'games': page_obj,
        'teams': teams,
        'selected_team': selected_team,
    }

    return render(request, 'schedule.html', context)
