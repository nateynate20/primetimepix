from django.utils import timezone
from datetime import timedelta, time
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from apps.games.models import Game
import pytz

# Define primetime start time (8:00 PM)
PRIMETIME_START = time(20, 0)

@login_required(login_url='login')
def view_schedule_page(request):
    now = timezone.now()

    # Get start (Monday) and end (next Monday) of current week
    week_start = now - timedelta(days=now.weekday())
    week_end = week_start + timedelta(days=7)

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

    context = {
        'games_with_info': [
            {'game': game, 'started': game.start_time <= now, 'user_pick': None}
            for game in primetime_games
        ],
    }
    return render(request, 'schedule.html', context)


@login_required(login_url='login')
def view_score(request):
    """Enhanced version with primetime filtering"""
    
    # Filter logic
    selected_team = request.GET.get('team', '').strip()
    games = Game.objects.all()

    # Filter games by team if a team is selected
    if selected_team:
        games = games.filter(
            Q(home_team__icontains=selected_team) | Q(away_team__icontains=selected_team)
        )

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
    return render(request, 'views_score.html', context)