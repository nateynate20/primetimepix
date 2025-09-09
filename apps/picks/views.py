# apps/picks/views.py

from datetime import timedelta
from django.utils import timezone
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q

from apps.games.models import Game
from apps.leagues.models import League
from .models import Pick
from .services import PickService


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
    Display NFL schedule with picks functionality.
    Shows all games for the current week, with option to filter to primetime only.
    """
    week_start, week_end = get_current_week_dates()

    # Base games queryset for the week
    base_games = Game.objects.filter(
        start_time__date__gte=week_start,
        start_time__date__lte=week_end,
    ).order_by("start_time")

    # Team filter
    selected_team = request.GET.get("team")
    if selected_team:
        base_games = base_games.filter(
            Q(home_team__icontains=selected_team) | Q(away_team__icontains=selected_team)
        )

    # Convert to list and apply primetime filter in Python
    games_list = list(base_games)
    show_primetime_only = request.GET.get("primetime") == "true"
    games = [g for g in games_list if g.is_primetime] if show_primetime_only else games_list

    # League selection
    league_id = request.GET.get("league") or request.POST.get("league")
    league = None
    if league_id:
        try:
            league = League.objects.get(id=league_id, is_approved=True, members=request.user)
        except League.DoesNotExist:
            messages.error(request, "Invalid or unauthorized league selected.")
            return redirect("display_nfl_schedule")

    user_leagues = League.objects.filter(members=request.user, is_approved=True)

    # Handle POST (save picks)
    if request.method == "POST":
        picks_data = {}
        for game in games:
            pick_key = f"pick_{game.id}"
            user_pick = request.POST.get(pick_key)
            if user_pick:
                picked_team = game.home_team if user_pick == "home" else game.away_team
                picks_data[game.id] = {"team": picked_team, "confidence": 1}

        if picks_data:
            saved, errors = PickService.save_user_picks(request.user, picks_data, league=league)
            if saved:
                messages.success(request, f"{len(saved)} pick(s) saved successfully.")
            if errors:
                for error in errors:
                    messages.warning(request, error)

        # Redirect to prevent duplicate submission
        query_params = []
        if selected_team:
            query_params.append(f"team={selected_team}")
        if show_primetime_only:
            query_params.append("primetime=true")
        if league_id:
            query_params.append(f"league={league_id}")

        redirect_url = request.path
        if query_params:
            redirect_url += "?" + "&".join(query_params)
        return redirect(redirect_url)

    # Enhance games with user picks and display info
    picks_dict = PickService.get_user_pick_status(request.user, games, league=league)

    for game in games:
        # Add display properties
        game.display_time_et = game.start_time_et
        game.game_week = game.week
        game.primetime_label = game.primetime_type if game.is_primetime else None

        # Pick-related properties
        game.user_pick = picks_dict.get(game.id)
        # NOTE: game.locked is handled by the Game model's property - no need to set it

        # Winner is automatically handled by the Game model's winner property

    # Pagination
    paginator = Paginator(games, 12)
    page_number = request.GET.get("page", 1)
    page_obj = paginator.get_page(page_number)

    # Stats
    total_games = len(games_list)
    primetime_count = sum(1 for g in games_list if g.is_primetime)
    completed_games = sum(1 for g in games if g.status == 'final')

    # Teams dropdown - extract team nicknames
    team_set = set()
    for g in games_list:
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
        "show_primetime_only": show_primetime_only,
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
    league = None
    if league_id:
        try:
            league = League.objects.get(id=league_id, members=request.user)
        except League.DoesNotExist:
            messages.error(request, "League not found or you're not a member.")
            return redirect("general_standings")

    leaderboard = PickService.calculate_leaderboard(league=league)
    paginator = Paginator(leaderboard, 20)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "page_obj": page_obj,
        "league": league,
        "is_overall": not league,
        "user_leagues": League.objects.filter(members=request.user, is_approved=True),
    }
    return render(request, "standings.html", context)


@login_required(login_url="login")
def general_standings(request):
    """Overall leaderboard"""
    leaderboard = PickService.calculate_leaderboard(league=None)
    paginator = Paginator(leaderboard, 20)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "page_obj": page_obj,
        "is_overall": True,
        "user_leagues": League.objects.filter(members=request.user, is_approved=True),
    }
    return render(request, "general_standings.html", context)