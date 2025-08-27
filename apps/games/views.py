from django.utils import timezone
from datetime import timedelta, time
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from apps.games.models import Game

# Define primetime start time (8:00 PM)
PRIMETIME_START = time(20, 0)

@login_required(login_url='login')
def view_schedule_page(request):
    now = timezone.now()

    # Get start (Monday) and end (next Monday) of current week
    week_start = now - timedelta(days=now.weekday())
    week_end = week_start + timedelta(days=7)

    # Filter games in this week starting at or after 8:00 PM (primetime)
    games = Game.objects.filter(
        start_time__gte=week_start,
        start_time__lt=week_end,
        start_time__time__gte=PRIMETIME_START
    ).order_by('start_time')

    context = {
        'games_with_info': [
            {'game': game, 'started': game.start_time <= now, 'user_pick': None}
            for game in games
        ],
    }
    return render(request, 'schedule.html', context)


@login_required(login_url='login')
def view_score(request):
    """Enhanced version of your existing view with gradual primetime additions"""
    
    # Your existing filter logic
    selected_team = request.GET.get('team', '').strip()
    games = Game.objects.all()

    # Filter games by team if a team is selected (your original logic)
    if selected_team:
        games = games.filter(
            Q(home_team__icontains=selected_team) | Q(away_team__icontains=selected_team)
        )

    # NEW: Add primetime filter option
    show_primetime_only = request.GET.get('primetime') == 'true'
    if show_primetime_only:
        # Filter for games that would be considered primetime
        # We'll do this in Python to use the model property if it exists
        all_games = list(games.order_by('-start_time'))
        primetime_games = []
        for game in all_games:
            if hasattr(game, 'is_primetime') and game.is_primetime:
                primetime_games.append(game)
            # Fallback if property doesn't exist - check if game starts at 8 PM or later
            elif not hasattr(game, 'is_primetime'):
                try:
                    # Convert to Eastern Time for comparison
                    import pytz
                    eastern = pytz.timezone('US/Eastern')
                    et_time = game.start_time.astimezone(eastern)
                    if et_time.time() >= time(20, 0):  # 8 PM ET
                        primetime_games.append(game)
                except:
                    # If timezone conversion fails, use simple time comparison
                    if game.start_time.time() >= time(20, 0):
                        primetime_games.append(game)
        
        # Convert back to queryset for pagination
        if primetime_games:
            game_ids = [game.id for game in primetime_games]
            games = Game.objects.filter(id__in=game_ids).order_by('-start_time')
        else:
            games = Game.objects.none()

    # Your existing team dropdown logic
    teams = Game.objects.values_list('home_team', flat=True).distinct().order_by('home_team')

    # NEW: Calculate some stats for the template
    total_games = Game.objects.count()
    try:
        all_nfl_games = list(Game.objects.all())
        primetime_count = 0
        for game in all_nfl_games:
            if hasattr(game, 'is_primetime') and game.is_primetime:
                primetime_count += 1
            elif not hasattr(game, 'is_primetime'):
                # Fallback calculation
                try:
                    import pytz
                    eastern = pytz.timezone('US/Eastern')
                    et_time = game.start_time.astimezone(eastern)
                    if et_time.time() >= time(20, 0):
                        primetime_count += 1
                except:
                    if game.start_time.time() >= time(20, 0):
                        primetime_count += 1
    except:
        primetime_count = 0

    # Your existing pagination logic
    paginator = Paginator(games.order_by('-start_time'), 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Enhanced context with new data
    context = {
        'games': page_obj,
        'teams': teams,
        'selected_team': selected_team,
        # NEW: Add primetime-related context
        'show_primetime_only': show_primetime_only,
        'total_games': total_games,
        'primetime_count': primetime_count,
    }
    return render(request, 'views_score.html', context)