# apps/picks/views.py
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.contrib import messages
from django.utils import timezone
from apps.games.models import Game
from apps.picks.models import Pick
from apps.leagues.models import League
from apps.picks.services import PickService  # Make sure this exists

@login_required
def display_nfl_schedule(request):
    user = request.user
    week_start = timezone.now().date()
    week_end = week_start + timezone.timedelta(days=6)

    # Filters
    league_id = request.GET.get('league')
    show_primetime_only = request.GET.get('primetime') == 'true'
    selected_team = request.GET.get('team')

    games = Game.objects.filter(start_time__date__range=[week_start, week_end]).order_by('start_time')

    if show_primetime_only:
        games = games.filter(is_primetime=True)

    league = None
    if league_id:
        try:
            league = League.objects.get(id=league_id)
        except League.DoesNotExist:
            league = None

    user_leagues = League.objects.filter(users=user)

    # Attach user picks to each game
    for game in games:
        try:
            if league:
                game.user_pick = Pick.objects.get(user=user, game=game, league=league)
            else:
                game.user_pick = Pick.objects.get(user=user, game=game)
        except Pick.DoesNotExist:
            game.user_pick = None

        # Determine winner flags for template
        game.away_is_winner = game.winner == game.away_team if game.winner else False
        game.home_is_winner = game.winner == game.home_team if game.winner else False
        game.has_score = game.status in ['final', 'in_progress']

    # Pagination
    paginator = Paginator(games, 9)  # 9 games per page
    page_number = request.GET.get('page')
    games_page = paginator.get_page(page_number)

    context = {
        'games': games_page,
        'week_start': week_start,
        'week_end': week_end,
        'total_games': games.count(),
        'completed_games': games.filter(status='final').count(),
        'primetime_count': games.filter(is_primetime=True).count(),
        'user_leagues': user_leagues,
        'league': league,
        'show_primetime_only': show_primetime_only,
        'selected_team': selected_team,
    }

    return render(request, 'schedule.html', context)


@login_required(login_url="login")
def standings(request):
    """League-specific leaderboard"""
    league_id = request.GET.get("league")
    league = None
    if league_id:
        try:
            league = League.objects.get(id=league_id, users=request.user)
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
        "user_leagues": League.objects.filter(users=request.user, is_approved=True),
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
        "user_leagues": League.objects.filter(users=request.user, is_approved=True),
    }
    return render(request, "general_standings.html", context)
