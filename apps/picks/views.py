# apps/picks/views.py

from datetime import timedelta
import pytz
from django.utils import timezone
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q

from apps.games.models import Game
from apps.leagues.models import League
from .models import Pick
from .services import PickService, PickValidationService


def get_current_week_dates():
    """Return start and end date of the current week (Monday-Sunday)."""
    today = timezone.now().date()
    days_since_monday = today.weekday()
    week_start = today - timedelta(days=days_since_monday)
    week_end = week_start + timedelta(days=6)
    return week_start, week_end


@login_required(login_url="login")
def display_nfl_schedule(request):
    """
    Display NFL schedule with primetime games only for picks.
    Supports optional team filtering and league selection.
    """
    week_start, week_end = get_current_week_dates()
    eastern = pytz.timezone('US/Eastern')

    # --- Base games queryset for the week ---
    base_games = Game.objects.filter(
        start_time__date__gte=week_start,
        start_time__date__lte=week_end,
        is_primetime=True  # Only primetime games
    ).order_by("start_time")

    # --- Team filter ---
    selected_team = request.GET.get("team")
    if selected_team:
        base_games = base_games.filter(
            Q(home_team__icontains=selected_team) | Q(away_team__icontains=selected_team)
        )

    games = list(base_games)

    # --- League selection ---
    league_id = request.GET.get("league") or request.POST.get("league")
    league = (
        League.objects.filter(id=league_id, is_approved=True, members=request.user).first()
        if league_id else None
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

        # Redirect preserving GET params
        query_params = ["primetime=true"]
        if selected_team:
            query_params.append(f"team={selected_team}")
        if league_id:
            query_params.append(f"league={league_id}")

        return redirect(f"{request.path}?{'&'.join(query_params)}")

    # --- Enhance games with user picks and display info ---
    picks_dict = PickService.get_user_pick_status(request.user, games, league=league)

    for game in games:
        # Convert UTC start_time to ET for display
        game.display_time_et = game.start_time.astimezone(eastern) if game.start_time else None
        game.game_week = game.week
        game.primetime_label = game.primetime_type

        # Pick-related properties
        game.user_pick = picks_dict.get(game.id)
        game.locked = not game.can_make_picks()

        # Determine winner if game is complete
        if game.status == 'final' and game.home_score is not None and game.away_score is not None:
            if game.home_score > game.away_score:
                game.winner = game.home_team
            elif game.away_score > game.home_score:
                game.winner = game.away_team
            else:
                game.winner = 'tie'
        else:
            game.winner = None

    # --- Pagination ---
    paginator = Paginator(games, 12)
    page_number = request.GET.get("page", 1)
    page_obj = paginator.get_page(page_number)

    # --- Stats ---
    total_games = len(games)
    primetime_count = len(games)
    completed_games = sum(1 for g in games if g.status == 'final')

    # --- Teams dropdown ---
    team_set = set()
    for g in games:
        if g.home_team.split():
            team_set.add(g.home_team.split()[-1])
        if g.away_team.split():
            team_set.add(g.away_team.split()[-1])
    teams = sorted(team_set)

    context = {
        "games": page_obj,
        "league": league,
        "user_leagues": user_leagues,
        "teams": teams,
        "selected_team": selected_team,
        "show_primetime_only": True,
        "total_games": total_games,
        "completed_games": completed_games,
        "primetime_count": primetime_count,
        "week_start": week_start,
        "week_end": week_end,
    }
    return render(request, "schedule.html", context)


@login_required(login_url="login")
def standings(request):
    """League-specific leaderboard"""
    league_id = request.GET.get("league")
    league = League.objects.filter(id=league_id, members=request.user).first() if league_id else None

    leaderboard = PickService.calculate_leaderboard(league=league)
    paginator = Paginator(leaderboard, 20)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "page_obj": page_obj,
        "league": league,
        "is_overall": not league,
    }
    return render(request, "standings.html", context)


@login_required(login_url="login")
def general_standings(request):
    """Overall leaderboard"""
    leaderboard = PickService.calculate_leaderboard(league=None)
    paginator = Paginator(leaderboard, 20)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {"page_obj": page_obj}
    return render(request, "general_standings.html", context)
