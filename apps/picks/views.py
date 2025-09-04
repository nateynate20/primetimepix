# apps/picks/views.py

from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q

from apps.games.models import Game
from apps.leagues.models import League
from .models import Pick
from .services import PickService
from apps.games.utils import is_primetime_game, get_current_week_dates


@login_required(login_url="login")
def display_nfl_schedule(request):
    """
    Display NFL schedule with optional primetime and team filters,
    allow picks, and maintain old naming conventions for consistency.
    """
    current_week_start, current_week_end = get_current_week_dates()

    # --- Filters ---
    selected_team = request.GET.get("team", "").strip()
    show_primetime_only = request.GET.get("primetime") == "true"

    # --- Base games queryset ---
    games_qs = Game.objects.filter(
        start_time__date__gte=current_week_start,
        start_time__date__lte=current_week_end,
    ).order_by("week", "start_time")

    if selected_team:
        games_qs = games_qs.filter(
            Q(home_team__icontains=selected_team) | Q(away_team__icontains=selected_team)
        )

    # --- Primetime filtering ---
    games = [g for g in games_qs if is_primetime_game(g)] if show_primetime_only else list(games_qs)

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
        "current_week_start": current_week_start,
        "current_week_end": current_week_end,
        "total_games": Game.objects.count(),
        "primetime_count": sum(1 for g in Game.objects.all() if is_primetime_game(g)),
    }
    return render(request, "schedule.html", context)


@login_required(login_url="login")
def standings(request):
    """
    League-specific standings. If no league is selected, shows overall.
    """
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
    """
    Overall leaderboard across all users.
    """
    leaderboard = PickService.calculate_leaderboard(league=None)
    paginator = Paginator(leaderboard, 20)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {"page_obj": page_obj}
    return render(request, "general_standings.html", context)
