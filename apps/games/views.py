from datetime import datetime, time, date, timedelta
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from nfl_schedule.models import Game

def get_thanksgiving_date(year):
    nov1 = date(year, 11, 1)
    first_thursday = nov1 + timedelta(days=(3 - nov1.weekday()) % 7)
    return first_thursday + timedelta(weeks=3)

@login_required(login_url='login')
def view_schedule_page(request):
    selected_team = request.GET.get('team', '').strip()

    today = datetime.now().date()
    year = today.year
    PRIMETIME_START = time(20, 0)  # 8 PM

    # Calculate holiday dates
    holiday_dates = [
        get_thanksgiving_date(year),
        date(year, 12, 25),
        date(year + 1 if today.month == 12 else year, 1, 1),
    ]

    # Filter only primetime or holiday games happening today or later
    upcoming_games = NFLGame.objects.filter(date__gte=today)
    primetime_games = upcoming_games.filter(start_time__gte=PRIMETIME_START)
    holiday_games = upcoming_games.filter(date__in=holiday_dates)

    games = primetime_games.union(holiday_games).order_by('date', 'start_time')

    # Optional: filter by team if selected
    if selected_team:
        games = games.filter(
            Q(home_team__icontains=selected_team) | Q(away_team__icontains=selected_team)
        )

    teams = NFLGame.objects.values_list('home_team', flat=True).distinct().order_by('home_team')

    paginator = Paginator(games, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'games': page_obj,
        'teams': teams,
        'selected_team': selected_team,
    }
    return render(request, 'schedule.html', context)
