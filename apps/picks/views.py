# apps/picks/views.py

from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.core.paginator import Paginator
from datetime import timedelta

from apps.games.models import Game
from apps.leagues.models import League
from .models import Pick
from .forms import PickForm

@login_required(login_url='login')
def display_nfl_schedule(request):
    now = timezone.now()

    week_start = now - timedelta(days=now.weekday())
    week_end = week_start + timedelta(days=7)

    games = Game.objects.filter(start_time__gte=week_start, start_time__lt=week_end).order_by('start_time')

    league_id = request.GET.get('league') or request.POST.get('league')
    league = None
    if league_id:
        league = League.objects.filter(id=league_id, is_approved=True, members=request.user).first()
        if not league:
            messages.error(request, "Invalid or unauthorized league selected.")
            return redirect('schedule')

    user_picks = Pick.objects.filter(user=request.user, game__in=games, league=league)
    picks_dict = {pick.game_id: pick.picked_team for pick in user_picks}

    if request.method == 'POST':
        for game in games:
            pick_key = f'pick_{game.id}'
            user_pick = request.POST.get(pick_key)
            if user_pick:
                if now >= game.start_time:
                    messages.warning(request, f"Picks for {game.away_team} @ {game.home_team} are closed because the game started.")
                    continue

                Pick.objects.update_or_create(
                    user=request.user,
                    game=game,
                    league=league,
                    defaults={'picked_team': user_pick}
                )
        messages.success(request, "Your picks have been saved.")
        return redirect('schedule')

    games_with_info = []
    for game in games:
        started = now >= game.start_time
        games_with_info.append({
            'game': game,
            'user_pick': picks_dict.get(game.id),
            'started': started,
        })

    context = {
        'games_with_info': games_with_info,
        'league': league,
    }
    return render(request, 'schedule.html', context)


@login_required(login_url='login')
def general_standings(request):
    """
    Placeholder for a global leaderboard across all users and leagues.
    Later, you can aggregate total correct picks for each user across all leagues.
    """
    return render(request, 'picks/general_standings.html')


@login_required(login_url='login')
def standings(request):
    """
    League-specific standings view.
    Later, you'll want to add logic to rank users based on performance in the league.
    """
    league_id = request.GET.get('league')
    if not league_id:
        messages.error(request, "No league selected.")
        return redirect('schedule')

    league = League.objects.filter(id=league_id, members=request.user).first()
    if not league:
        messages.error(request, "Invalid or unauthorized league selected.")
        return redirect('schedule')

    # Placeholder — update this with pick stats later
    context = {
        'league': league,
    }
    return render(request, 'picks/standings.html', context)
