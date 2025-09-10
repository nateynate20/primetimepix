# apps/picks/views.py - Updated with NFL week support
from datetime import timedelta
from django.utils import timezone
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q

from apps.games.models import Game
from apps.games.utils import get_current_week_dates, get_current_nfl_week, get_nfl_week_dates
from apps.leagues.models import League
from .models import Pick
from .services import PickService


@login_required(login_url="login")
def display_nfl_schedule(request):
    """
    Display NFL primetime schedule with picks functionality.
    Shows ONLY PRIMETIME games for the current NFL week for making picks.
    """
    # Get current NFL week or allow week selection
    week_number = request.GET.get('week')
    if week_number:
        try:
            week_number = int(week_number)
            week_start, week_end = get_nfl_week_dates(week_number)
        except (ValueError, TypeError):
            week_start, week_end = get_current_week_dates()
            week_number = get_current_nfl_week()
    else:
        week_start, week_end = get_current_week_dates()
        week_number = get_current_nfl_week()

    # Base games queryset for the NFL week
    all_games = Game.objects.filter(
        start_time__date__gte=week_start,
        start_time__date__lte=week_end,
    ).order_by("start_time")

    # Debug: Print what we're finding
    print(f"NFL Week {week_number}: {week_start} to {week_end}")
    print(f"Total games found: {all_games.count()}")
    
    # Filter to ONLY primetime games for picks
    primetime_games = []
    for game in all_games:
        if game.is_primetime:
            primetime_games.append(game)
            print(f"Primetime: {game.away_team} @ {game.home_team} - {game.display_time_et}")

    print(f"Primetime games found: {len(primetime_games)}")

    # Team filter (still applies to primetime games)
    selected_team = request.GET.get("team")
    if selected_team:
        primetime_games = [
            game for game in primetime_games 
            if selected_team.lower() in game.home_team.lower() or selected_team.lower() in game.away_team.lower()
        ]

    # League selection
    league_id = request.GET.get("league") or request.POST.get("league")
    league = None
    if league_id:
        try:
            league = League.objects.get(id=league_id, is_approved=True, members=request.user)
        except League.DoesNotExist:
            messages.error(request, "Invalid or unauthorized league selected.")
            return redirect("schedule")

    user_leagues = League.objects.filter(members=request.user, is_approved=True)

    # Handle POST (save picks)
    if request.method == "POST":
        picks_data = {}
        for game in primetime_games:
            pick_key = f"pick_{game.id}"
            user_pick = request.POST.get(pick_key)
            if user_pick:
                picked_team = game.home_team if user_pick == "home" else game.away_team
                picks_data[game.id] = {"team": picked_team, "confidence": 1}

        if picks_data:
            saved, errors = PickService.save_user_picks(request.user, picks_data, league=league)
            if saved:
                messages.success(request, f"{len(saved)} primetime pick(s) saved successfully.")
            if errors:
                for error in errors:
                    messages.warning(request, error)

        # Redirect to prevent duplicate submission
        query_params = []
        if selected_team:
            query_params.append(f"team={selected_team}")
        if league_id:
            query_params.append(f"league={league_id}")
        if week_number:
            query_params.append(f"week={week_number}")

        redirect_url = request.path
        if query_params:
            redirect_url += "?" + "&".join(query_params)
        return redirect(redirect_url)

    # Enhance games with user picks and display info
    picks_dict = PickService.get_user_pick_status(request.user, primetime_games, league=league)

    for game in primetime_games:
        # Pick-related properties
        game.user_pick = picks_dict.get(game.id)
        
        # Add template-friendly properties
        game.game_week = game.week
        game.primetime_label = game.primetime_type if game.is_primetime else None
        
        # For score display
        game.has_score = game.status in ['final', 'in_progress'] and (game.home_score is not None or game.away_score is not None)
        game.away_is_winner = game.winner == game.away_team if game.winner else False
        game.home_is_winner = game.winner == game.home_team if game.winner else False

    # Pagination
    paginator = Paginator(primetime_games, 12)
    page_number_param = request.GET.get("page", 1)
    page_obj = paginator.get_page(page_number_param)

    # Stats - based on all games in the week for context
    total_games = len(all_games)
    primetime_count = len(primetime_games)
    completed_games = sum(1 for g in primetime_games if g.status == 'final')

    # Teams dropdown - extract team nicknames from primetime games
    team_set = set()
    for g in primetime_games:
        if g.home_team.split():
            team_set.add(g.home_team.split()[-1])
        if g.away_team.split():
            team_set.add(g.away_team.split()[-1])
    teams = sorted(team_set)

    # Week navigation
    available_weeks = list(range(1, 19))  # NFL weeks 1-18
    
    context = {
        "games": page_obj,
        "league": league,
        "user_leagues": user_leagues,
        "teams": teams,
        "selected_team": selected_team,
        "show_primetime_only": True,  # Always true for picks page
        "total_games": total_games,
        "completed_games": completed_games,
        "primetime_count": primetime_count,
        "week_start": week_start,
        "week_end": week_end,
        "current_week": week_number,
        "available_weeks": available_weeks,
        "is_picks_page": True,  # Flag to help template know this is picks page
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