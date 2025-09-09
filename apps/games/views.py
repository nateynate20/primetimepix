from datetime import timedelta
from django.utils import timezone
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from .models import Game

def get_current_week_dates():
    today = timezone.now().date()
    days_since_monday = today.weekday()
    week_start = today - timedelta(days=days_since_monday)
    week_end = week_start + timedelta(days=6)
    return week_start, week_end

@login_required
def weekly_primetime_view(request):
    week_start, week_end = get_current_week_dates()

    base_games = Game.objects.filter(
        start_time__date__gte=week_start,
        start_time__date__lte=week_end,
    ).order_by('start_time')

    selected_team = request.GET.get('team')
    if selected_team:
        base_games = base_games.filter(
            Q(home_team__icontains=selected_team) |
            Q(away_team__icontains=selected_team)
        )

    show_primetime_only = request.GET.get('primetime') == 'true'
    games = [g for g in base_games if g.is_primetime] if show_primetime_only else list(base_games)

    for game in games:
        game.display_time_et = game.start_time_et
        game.game_week = game.week

    paginator = Paginator(games, 12)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    total_games = len(list(base_games))
    primetime_count = sum(1 for g in base_games if g.is_primetime)

    # Teams dropdown
    team_set = set()
    for g in base_games:
        if g.home_team.split():
            team_set.add(g.home_team.split()[-1])
        if g.away_team.split():
            team_set.add(g.away_team.split()[-1])
    teams = sorted(team_set)

    context = {
        'games': page_obj,
        'teams': teams,
        'selected_team': selected_team,
        'show_primetime_only': show_primetime_only,
        'total_games': total_games,
        'primetime_count': primetime_count,
        'week_start': week_start,
        'week_end': week_end,
    }
    return render(request, 'schedule.html', context)


@login_required
def weekly_score_view(request):
    week_start, week_end = get_current_week_dates()

    games_qs = Game.objects.filter(
        start_time__date__gte=week_start,
        start_time__date__lte=week_end,
    ).order_by('-start_time')

    selected_team = request.GET.get('team')
    if selected_team:
        games_qs = games_qs.filter(
            Q(home_team__icontains=selected_team) |
            Q(away_team__icontains=selected_team)
        )

    show_primetime_only = request.GET.get('primetime') == 'true'
    games_list = [g for g in games_qs if g.is_primetime] if show_primetime_only else list(games_qs)

    for game in games_list:
        game.display_time_et = game.start_time_et
        game.game_week = game.week
        game.primetime_label = game.primetime_type if game.is_primetime else None

    paginator = Paginator(games_list, 12)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    total_games = len(games_list)
    completed_games = sum(1 for g in games_list if g.is_finished)
    primetime_count = sum(1 for g in games_list if g.is_primetime)

    # Teams dropdown
    team_set = set()
    for g in games_qs:
        if g.home_team.split():
            team_set.add(g.home_team.split()[-1])
        if g.away_team.split():
            team_set.add(g.away_team.split()[-1])
    teams = sorted(team_set)

    context = {
        'games': page_obj,
        'teams': teams,
        'selected_team': selected_team,
        'show_primetime_only': show_primetime_only,
        'total_games': total_games,
        'completed_games': completed_games,
        'primetime_count': primetime_count,
        'week_start': week_start,
        'week_end': week_end,
    }
    return render(request, 'views_score.html', context)
