# apps/picks/views.py
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.utils import timezone

from apps.games.models import Game
from apps.leagues.models import League
from .models import Pick
from .services import PickService, StatsService
from apps.games.utils import filter_primetime_games, get_current_nfl_week


@login_required(login_url="login")
def display_nfl_schedule(request):
    """Display NFL schedule with primetime filtering, picks, and scores"""
    current_week = get_week_date_range()

    # --- Filters ---
    selected_team = request.GET.get("team", "").strip()
    show_primetime_only = request.GET.get("primetime") == "true"

    games_qs = Game.objects.filter(sport="NFL").order_by("game_week", "start_time")
    if selected_team:
        games_qs = games_qs.filter(
            home_team__icontains=selected_team
        ) | games_qs.filter(away_team__icontains=selected_team)

    # --- Primetime filtering ---
    games = is_datetime_primetime(games_qs) if show_primetime_only else list(games_qs)

    # --- League selection ---
    league_id = request.GET.get("league") or request.POST.get("league")
    league = (
        League.objects.filter(id=league_id, is_approved=True, members=request.user).first()
        if league_id
        else None
    )
    if league_id and not league:
        messages.error(request, "Invalid or unauthorized league selected.")
        return redirect("schedule")

    user_leagues = League.objects.filter(members=request.user, is_approved=True)

    # --- Handle POST (save picks) ---
    if request.method == "POST":
        picks_data = {}
        for game in games:
            pick_key = f"pick_{game.id}"
            user_pick = request.POST.get(pick_key)
            if not user_pick:
                continue

            picked_team = game.home_team if user_pick == "home" else game.away_team
            picks_data[game.id] = {"team": picked_team, "confidence": 1}

        saved, errors = PickService.save_user_picks(request.user, picks_data, league=league)
        if saved:
            messages.success(request, f"{len(saved)} pick(s) saved.")
        if errors:
            for e in errors:
                messages.warning(request, e)
        return redirect("schedule")

    # --- Attach user pick status ---
    picks_dict = PickService.get_user_pick_status(request.user, games, league=league)
    for game in games:
        game.user_pick = picks_dict.get(game.id, {}).get("picked_team")
        game.locked = not game.can_make_picks()

    # --- Pagination ---
    paginator = Paginator(games, 12)
    page_number = request.GET.get("page")
    games_page = paginator.get_page(page_number)

    context = {
        "games": games_page,
        "league": league,
        "user_leagues": user_leagues,
        "teams": Game.objects.values_list("home_team", flat=True).distinct().order_by("home_team"),
        "selected_team": selected_team,
        "show_primetime_only": show_primetime_only,
        "current_week": current_week,
        "total_games": Game.objects.count(),
        "primetime_count": len(is_datetime_primetime(Game.objects.all())),
    }
    return render(request, "picks/schedule.html", context)


@login_required(login_url="login")
def standings(request):
    league_id = request.GET.get('league')
    league = None
    if league_id:
        league = League.objects.filter(id=league_id, members=request.user).first()

    # Get all picks for finished games
    picks_query = Pick.objects.filter(
        game__status='finished',
        is_correct__isnull=False
    )
    
    if league:
        picks_query = picks_query.filter(league=league)

    # Calculate standings
    standings_dict = {}
    for pick in picks_query:
        user_stats = standings_dict.setdefault(pick.user_id, {
            'username': pick.user.username,
            'correct': 0,
            'total': 0,
            'percentage': 0,
            'points': 0
        })
        
        user_stats['total'] += 1
        if pick.is_correct:
            user_stats['correct'] += 1
            user_stats['points'] += pick.points
        
        user_stats['percentage'] = (user_stats['correct'] / user_stats['total']) * 100

    # Sort by points, then percentage
    standings = sorted(
        standings_dict.values(),
        key=lambda x: (-x['points'], -x['percentage'])
    )

    context = {
        'standings': standings,
        'league': league,
        'is_overall': not league
    }
    return render(request, 'standings.html', context)


@login_required(login_url="login")
def general_standings(request):
    """Overall leaderboard across all users"""
    leaderboard = PickService.calculate_leaderboard(league=None)
    paginator = Paginator(leaderboard, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {"page_obj": page_obj}
    return render(request, "picks/general_standings.html", context)


@login_required
def view_schedule_page(request):
    now = timezone.now()
    games = Game.objects.filter(start_time__gte=now).order_by('start_time')
    user_picks = Pick.objects.filter(user=request.user, game__in=games)
    picks_dict = {pick.game_id: pick.picked_team for pick in user_picks}
    games_with_info = []
    for game in games:
        started = now >= game.start_time
        games_with_info.append({
            'game': game,
            'user_pick': picks_dict.get(game.id),
            'started': started,
        })
    context = {'games_with_info': games_with_info}
    return render(request, 'schedule.html', context)

@login_required
def save_picks(request):
    if request.method != 'POST':
        return redirect('schedule')
        
    league_id = request.POST.get('league')
    league = None
    if league_id:
        league = League.objects.filter(id=league_id, members=request.user).first()

    now = timezone.now()
    picks_made = 0

    for key, value in request.POST.items():
        if key.startswith('pick_'):
            game_id = key.replace('pick_', '')
            try:
                game = Game.objects.get(id=game_id)
                if game.start_time <= now:
                    messages.error(request, f"Cannot make pick for {game} - game has started")
                    continue

                Pick.objects.update_or_create(
                    user=request.user,
                    game=game,
                    league=league,
                    defaults={'picked_team': value}
                )
                picks_made += 1
            except Game.DoesNotExist:
                continue

    if picks_made:
        messages.success(request, f"Successfully saved {picks_made} picks!")
    
    return redirect('schedule')
