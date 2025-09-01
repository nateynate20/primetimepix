<<<<<<< HEAD
# games/views.py

from datetime import datetime, time, date, timedelta
=======
from django.utils import timezone
from datetime import timedelta, time
>>>>>>> 80abcf7c5cfbf6c12ebf84c535599e472ccfb913
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from apps.games.models import Game
import pytz

<<<<<<< HEAD

def get_thanksgiving_date(year):
    """Returns the date of Thanksgiving (4th Thursday in November)."""
    nov1 = date(year, 11, 1)
    first_thursday = nov1 + timedelta(days=(3 - nov1.weekday()) % 7)
    return first_thursday + timedelta(weeks=3)
=======
# Define primetime start time (8:00 PM)
PRIMETIME_START = time(20, 0)
>>>>>>> 80abcf7c5cfbf6c12ebf84c535599e472ccfb913


@login_required(login_url='login')
def view_schedule_page(request):
    now = timezone.now()

<<<<<<< HEAD
    today = datetime.now().date()
    year = today.year
    PRIMETIME_START = time(20, 0)  # 8 PM kickoff
=======
    # Get start (Monday) and end (next Monday) of current week
    week_start = now - timedelta(days=now.weekday())
    week_end = week_start + timedelta(days=7)
>>>>>>> 80abcf7c5cfbf6c12ebf84c535599e472ccfb913

<<<<<<< HEAD
    # Define holiday dates (Thanksgiving, Christmas, New Year's)
    holiday_dates = [
        get_thanksgiving_date(year),
        date(year, 12, 25),
        date(year + 1 if today.month == 12 else year, 1, 1),
    ]
=======
    # Filter games in this week starting at or after 8:00 PM (primetime)
    eastern = pytz.timezone('US/Eastern')
    all_games = Game.objects.filter(
        start_time__gte=week_start,
        start_time__lt=week_end,
    ).order_by('start_time')
    
    # Filter for primetime games
    primetime_games = []
    for game in all_games:
        try:
            et_time = game.start_time.astimezone(eastern)
            if et_time.time() >= PRIMETIME_START:
                primetime_games.append(game)
        except:
            if hasattr(game, 'is_primetime') and game.is_primetime:
                primetime_games.append(game)
>>>>>>> 80abcf7c5cfbf6c12ebf84c535599e472ccfb913

<<<<<<< HEAD
    # Filter for games today or later
    upcoming_games = Game.objects.filter(date__gte=today)
    primetime_games = upcoming_games.filter(start_time__gte=PRIMETIME_START)
    holiday_games = upcoming_games.filter(date__in=holiday_dates)
=======
    context = {
        'games_with_info': [
            {'game': game, 'started': game.start_time <= now, 'user_pick': None}
            for game in primetime_games
        ],
    }
    return render(request, 'schedule.html', context)
>>>>>>> 80abcf7c5cfbf6c12ebf84c535599e472ccfb913

<<<<<<< HEAD
    # Combine and order games
    games = primetime_games.union(holiday_games).order_by('date', 'start_time')
=======
>>>>>>> 80abcf7c5cfbf6c12ebf84c535599e472ccfb913

<<<<<<< HEAD
    # Optional team filtering
=======
@login_required(login_url='login')
def view_score(request):
    """Enhanced version with primetime filtering"""
    
    # Filter logic
    selected_team = request.GET.get('team', '').strip()
    games = Game.objects.all()

    # Filter games by team if a team is selected
>>>>>>> 80abcf7c5cfbf6c12ebf84c535599e472ccfb913
    if selected_team:
        games = games.filter(
            Q(home_team__icontains=selected_team) |
            Q(away_team__icontains=selected_team)
        )

<<<<<<< HEAD
    # List of unique teams for filtering options
    teams = Game.objects.values_list('home_team', flat=True).distinct().order_by('home_team')
=======
    # Primetime filter option
    show_primetime_only = request.GET.get('primetime') == 'true'
    if show_primetime_only:
        # Filter for primetime games using the model property
        all_games = list(games.order_by('-start_time'))
        primetime_games = []
        eastern = pytz.timezone('US/Eastern')
        
        for game in all_games:
            try:
                # Use model property if available
                if hasattr(game, 'is_primetime') and game.is_primetime:
                    primetime_games.append(game)
                else:
                    # Fallback: manual check
                    et_time = game.start_time.astimezone(eastern)
                    if et_time.time() >= PRIMETIME_START:
                        primetime_games.append(game)
            except Exception:
                # Last fallback
                if game.start_time.time() >= PRIMETIME_START:
                    primetime_games.append(game)
        
        # Convert back to queryset for pagination
        if primetime_games:
            game_ids = [game.id for game in primetime_games]
            games = Game.objects.filter(id__in=game_ids).order_by('-start_time')
        else:
            games = Game.objects.none()
>>>>>>> 80abcf7c5cfbf6c12ebf84c535599e472ccfb913

<<<<<<< HEAD
    # Pagination
    paginator = Paginator(games, 10)
=======
    # Team dropdown
    teams = Game.objects.values_list('home_team', flat=True).distinct().order_by('home_team')

    # Calculate stats
    total_games = Game.objects.count()
    try:
        # Count primetime games efficiently
        eastern = pytz.timezone('US/Eastern')
        all_nfl_games = list(Game.objects.filter(sport='NFL'))
        primetime_count = 0
        
        for game in all_nfl_games:
            try:
                if hasattr(game, 'is_primetime') and game.is_primetime:
                    primetime_count += 1
                else:
                    et_time = game.start_time.astimezone(eastern)
                    if et_time.time() >= PRIMETIME_START:
                        primetime_count += 1
            except Exception:
                if game.start_time.time() >= PRIMETIME_START:
                    primetime_count += 1
    except Exception:
        primetime_count = 0

    # Pagination
    paginator = Paginator(games.order_by('-start_time'), 12)
>>>>>>> 80abcf7c5cfbf6c12ebf84c535599e472ccfb913
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'games': page_obj,
        'teams': teams,
        'selected_team': selected_team,
        'show_primetime_only': show_primetime_only,
        'total_games': total_games,
        'primetime_count': primetime_count,
    }
<<<<<<< HEAD

    return render(request, 'schedule.html', context)

=======
    return render(request, 'views_score.html', context)
>>>>>>> 80abcf7c5cfbf6c12ebf84c535599e472ccfb913