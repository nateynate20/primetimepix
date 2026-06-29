# apps/picks/views.py - Updated with NFL week support
from collections import OrderedDict
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
    Supports two view modes:
    - 'week' (default): Shows primetime games for a single NFL week.
    - 'season': Shows ALL primetime games across the full season, grouped by week.
    Games are pickable until their individual kickoff time.
    """
    view_mode = request.GET.get('view', 'week')  # 'week' or 'season'

    # League selection (shared between both modes)
    league_id = request.GET.get("league") or request.POST.get("league")
    league = None
    if league_id:
        try:
            league = League.objects.get(id=league_id, is_approved=True, members=request.user)
        except League.DoesNotExist:
            messages.error(request, "Invalid or unauthorized league selected.")
            return redirect("schedule")

    user_leagues = League.objects.filter(members=request.user, is_approved=True)

    # Team filter
    selected_team = request.GET.get("team")

    if view_mode == 'season':
        # FULL SEASON MODE: all primetime games across all weeks
        day_filter = ''

        regular_games = Game.objects.filter(game_type='regular').order_by("week", "start_time")
        playoff_games = Game.objects.filter(game_type='playoff').order_by("week", "start_time")

        all_primetime = [g for g in regular_games if g.is_primetime]
        all_primetime += [g for g in playoff_games if g.is_primetime]
        primetime_games = all_primetime

        if selected_team:
            primetime_games = [
                g for g in primetime_games
                if selected_team.lower() in g.home_team.lower() or selected_team.lower() in g.away_team.lower()
            ]

        # Group regular season games by week, then playoffs as one group
        games_by_week = OrderedDict()
        for game in primetime_games:
            if game.game_type == 'playoff':
                key = 'playoffs'
            else:
                key = game.week
            if key not in games_by_week:
                games_by_week[key] = []
            games_by_week[key].append(game)

        week_number = None
        week_start = None
        week_end = None
        all_games = list(regular_games) + list(playoff_games)
    else:
        # SINGLE WEEK MODE (default) - always start at Week 1
        # Shows games for the selected week, with optional day filter
        week_param = request.GET.get('week')
        day_filter = request.GET.get('day', '')  # '', 'thursday', 'sunday', 'monday'
        is_playoffs = (week_param == 'playoffs')

        if is_playoffs:
            week_number = 'playoffs'
            week_start = None
            week_end = None
            all_games = list(Game.objects.filter(game_type='playoff').order_by("start_time"))
        elif week_param:
            try:
                week_number = int(week_param)
            except (ValueError, TypeError):
                week_number = 1
            all_games = list(Game.objects.filter(
                game_type='regular', week=week_number
            ).order_by("start_time"))
            week_start, week_end = get_nfl_week_dates(week_number)
        else:
            week_number = get_current_nfl_week()
            all_games = list(Game.objects.filter(
                game_type='regular', week=week_number
            ).order_by("start_time"))
            week_start, week_end = get_nfl_week_dates(week_number)

        primetime_games = [g for g in all_games if g.is_primetime]

        # Apply day filter
        if day_filter and day_filter != 'all':
            if day_filter == 'sunday':
                all_games = [g for g in all_games if g.is_primetime and g.display_time_et and g.display_time_et.weekday() == 6]
            else:
                day_map = {
                    'thursday': 3,   # Thursday = weekday 3
                    'monday': 0,     # Monday = weekday 0
                }
                target_weekday = day_map.get(day_filter)
                if target_weekday is not None:
                    all_games = [g for g in all_games if g.display_time_et and g.display_time_et.weekday() == target_weekday]
            primetime_games = [g for g in all_games if g.is_primetime]

        if selected_team:
            all_games = [
                g for g in all_games
                if selected_team.lower() in g.home_team.lower() or selected_team.lower() in g.away_team.lower()
            ]
            primetime_games = [g for g in all_games if g.is_primetime]

        games_by_week = None

    # Handle POST (save picks) - works in both modes
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

        query_params = [f"view={view_mode}"]
        if selected_team:
            query_params.append(f"team={selected_team}")
        if league_id:
            query_params.append(f"league={league_id}")
        if week_number:
            query_params.append(f"week={week_number}")
        if day_filter:
            query_params.append(f"day={day_filter}")

        redirect_url = request.path + "?" + "&".join(query_params)
        return redirect(redirect_url)

    # Enhance games with user picks and display info
    picks_dict = PickService.get_user_pick_status(request.user, primetime_games, league=league)
    now = timezone.now()

    # In week mode, show primetime games by default; show all only when 'all' filter is active
    if view_mode == 'week':
        if day_filter == 'all':
            display_games = all_games
        else:
            display_games = primetime_games
    else:
        display_games = primetime_games

    for game in display_games:
        game.user_pick = picks_dict.get(game.id)
        game.game_week = game.week
        game.primetime_label = game.primetime_type if game.is_primetime else None
        game.has_score = game.status in ['final', 'in_progress'] and (game.home_score is not None or game.away_score is not None)
        game.away_is_winner = game.winner == game.away_team if game.winner else False
        game.home_is_winner = game.winner == game.home_team if game.winner else False
        # Only primetime games are pickable
        game.is_pickable = game.is_primetime and game.start_time > now and game.status == 'scheduled'
        # Mark placeholder times (midnight = ESPN hasn't set real kickoff yet)
        if game.display_time_et:
            game.time_is_tbd = (game.display_time_et.hour == 0 and game.display_time_et.minute == 0)
        else:
            game.time_is_tbd = True

    # Group games by date for ESPN-style display
    if view_mode != 'season':
        games_by_date = OrderedDict()
        for game in display_games:
            date_key = game.display_time_et.strftime('%A, %B %-d, %Y') if game.display_time_et else 'TBD'
            if date_key not in games_by_date:
                games_by_date[date_key] = []
            games_by_date[date_key].append(game)
    else:
        games_by_date = None

    # Pagination (only for season mode; week mode uses date grouping)
    if view_mode == 'season':
        page_obj = primetime_games
    else:
        page_obj = display_games

    # Stats
    total_games = Game.objects.count() if view_mode == 'season' else len(all_games)
    primetime_count = len(primetime_games)
    completed_games = sum(1 for g in display_games if g.status == 'final')

    # Teams dropdown - from all games in week mode
    team_set = set()
    for g in display_games:
        if g.home_team.split():
            team_set.add(g.home_team.split()[-1])
        if g.away_team.split():
            team_set.add(g.away_team.split()[-1])
    teams = sorted(team_set)

    # Week navigation - regular weeks 1-18 plus "Playoffs" if they exist
    available_weeks = list(range(1, 19))
    has_playoffs = Game.objects.filter(game_type='playoff').exists()

    # Build week info with date ranges for the nav
    week_info = []
    for wk in available_weeks:
        wk_games = Game.objects.filter(game_type='regular', week=wk).order_by('start_time')
        if wk_games.exists():
            first_date = wk_games.first().start_time.date()
            last_date = wk_games.last().start_time.date()
            week_info.append({'num': wk, 'start': first_date, 'end': last_date})
        else:
            week_info.append({'num': wk, 'start': None, 'end': None})

    context = {
        "games": page_obj,
        "games_by_week": games_by_week,
        "games_by_date": games_by_date,
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
        "current_week": week_number,
        "available_weeks": available_weeks,
        "week_info": week_info,
        "has_playoffs": has_playoffs,
        "day_filter": day_filter if view_mode == 'week' else '',
        "view_mode": view_mode,
        "is_picks_page": True,
    }
    return render(request, "schedule.html", context)


@login_required(login_url="login")
def standings(request):
    """League-specific leaderboard with optional weekly filter"""
    from apps.games.models import Game

    league_id = request.GET.get("league")
    league = None
    if league_id:
        try:
            league = League.objects.get(id=league_id, members=request.user)
        except League.DoesNotExist:
            messages.error(request, "League not found or you're not a member.")
            return redirect("general_standings")

    week_param = request.GET.get("week")
    selected_week = int(week_param) if week_param and week_param.isdigit() else None

    leaderboard = PickService.calculate_leaderboard(league=league, week=selected_week)
    paginator = Paginator(leaderboard, 20)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    available_weeks = list(
        Game.objects.filter(game_type='regular', status='final')
        .values_list('week', flat=True)
        .distinct()
        .order_by('week')
    )

    context = {
        "page_obj": page_obj,
        "league": league,
        "is_overall": not league,
        "selected_week": selected_week,
        "available_weeks": available_weeks,
        "user_leagues": League.objects.filter(members=request.user, is_approved=True),
    }
    return render(request, "standings.html", context)


@login_required(login_url="login")
def general_standings(request):
    """Overall leaderboard with optional weekly filter"""
    from apps.games.models import Game

    week_param = request.GET.get("week")
    selected_week = int(week_param) if week_param and week_param.isdigit() else None

    leaderboard = PickService.calculate_leaderboard(league=None, week=selected_week)
    paginator = Paginator(leaderboard, 20)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    available_weeks = list(
        Game.objects.filter(game_type='regular', status='final')
        .values_list('week', flat=True)
        .distinct()
        .order_by('week')
    )

    context = {
        "page_obj": page_obj,
        "is_overall": True,
        "selected_week": selected_week,
        "available_weeks": available_weeks,
        "user_leagues": League.objects.filter(members=request.user, is_approved=True),
    }
    return render(request, "general_standings.html", context)


@login_required(login_url="login")
def vs_cpu(request):
    """Head-to-head comparison page: user vs CPU picks."""
    from apps.picks.models import CPUPick
    from collections import OrderedDict

    profile = request.user.profile
    if not profile.cpu_challenge_active:
        profile.cpu_challenge_active = True
        profile.save()

    week_param = request.GET.get('week')

    # Get all CPU picks with their games
    cpu_picks_qs = CPUPick.objects.select_related('game').order_by('game__week', 'game__start_time')

    # Get user picks (no league = global picks)
    user_picks_qs = Pick.objects.filter(user=request.user).select_related('game')
    user_picks_dict = {p.game_id: p for p in user_picks_qs}

    # Build week-by-week comparison
    weeks_data = OrderedDict()
    user_wins = 0
    cpu_wins = 0
    ties = 0

    for cpu_pick in cpu_picks_qs:
        game = cpu_pick.game
        week_key = game.week if game.game_type == 'regular' else 'playoffs'

        if week_param:
            if week_param == 'playoffs' and week_key != 'playoffs':
                continue
            elif week_param != 'playoffs':
                try:
                    if week_key != int(week_param):
                        continue
                except (ValueError, TypeError):
                    pass

        if week_key not in weeks_data:
            weeks_data[week_key] = []

        user_pick = user_picks_dict.get(game.id)

        # Determine result
        result = None
        if game.status == 'final' and game.winner and game.winner != 'tie':
            if user_pick and cpu_pick.is_correct is not None:
                user_correct = user_pick.is_correct
                cpu_correct = cpu_pick.is_correct
                if user_correct and not cpu_correct:
                    result = 'user_win'
                    user_wins += 1
                elif cpu_correct and not user_correct:
                    result = 'cpu_win'
                    cpu_wins += 1
                elif user_correct and cpu_correct:
                    result = 'both_correct'
                    ties += 1
                else:
                    result = 'both_wrong'
                    ties += 1

        weeks_data[week_key].append({
            'game': game,
            'cpu_pick': cpu_pick.picked_team,
            'user_pick': user_pick.picked_team if user_pick else None,
            'result': result,
            'game_final': game.status == 'final',
            'winner': game.winner if game.status == 'final' else None,
        })

    # CPU overall stats
    total_cpu_picks = cpu_picks_qs.filter(is_correct__isnull=False).count()
    cpu_correct_count = cpu_picks_qs.filter(is_correct=True).count()
    cpu_accuracy = round((cpu_correct_count / total_cpu_picks * 100), 1) if total_cpu_picks > 0 else 0

    # User overall stats (for primetime games only)
    user_primetime_picks = [p for p in user_picks_qs if p.game.is_primetime and p.is_correct is not None]
    user_correct_count = sum(1 for p in user_primetime_picks if p.is_correct)
    user_total = len(user_primetime_picks)
    user_accuracy = round((user_correct_count / user_total * 100), 1) if user_total > 0 else 0

    context = {
        'weeks_data': weeks_data,
        'user_wins': user_wins,
        'cpu_wins': cpu_wins,
        'ties': ties,
        'total_matchups': user_wins + cpu_wins + ties,
        'cpu_accuracy': cpu_accuracy,
        'cpu_correct_count': cpu_correct_count,
        'total_cpu_picks': total_cpu_picks,
        'user_accuracy': user_accuracy,
        'user_correct_count': user_correct_count,
        'user_total_picks': user_total,
        'selected_week': week_param,
    }
    return render(request, "vs_cpu.html", context)


@login_required(login_url="login")
def toggle_cpu_challenge(request):
    """Toggle CPU challenge on/off for the user."""
    profile = request.user.profile
    profile.cpu_challenge_active = not profile.cpu_challenge_active
    profile.save()
    if profile.cpu_challenge_active:
        messages.success(request, "CPU Challenge activated! See how you stack up against the spread.")
        return redirect('vs_cpu')
    else:
        messages.info(request, "CPU Challenge deactivated.")
        return redirect('dashboard')