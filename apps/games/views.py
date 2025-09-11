from datetime import timedelta
from django.utils import timezone
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from .models import Game

def get_current_week_dates():
    """Return the start and end date of the current week (Mon-Sun)."""
    today = timezone.now().date()
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)
    return week_start, week_end

def get_filtered_games(request, queryset):
    """Filter games by team and primetime flag from request."""
    selected_team = request.GET.get('team')
    if selected_team:
        queryset = queryset.filter(
            Q(home_team__icontains=selected_team) |
            Q(away_team__icontains=selected_team)
        )

    show_primetime_only = request.GET.get('primetime') == 'true'
    if show_primetime_only:
        queryset = [g for g in queryset if g.is_primetime]
    else:
        queryset = list(queryset)

    return queryset, selected_team, show_primetime_only

def get_teams_dropdown(games_queryset):
    """Return sorted list of team last names for dropdown."""
    team_set = set()
    for g in games_queryset:
        if g.home_team.split():
            team_set.add(g.home_team.split()[-1])
        if g.away_team.split():
            team_set.add(g.away_team.split()[-1])
    return sorted(team_set)

@login_required
def weekly_primetime_view(request):
    """Display weekly primetime schedule."""
    week_start, week_end = get_current_week_dates()

    base_games = Game.objects.filter(
        start_time__date__gte=week_start,
        start_time__date__lte=week_end,
    ).order_by('start_time')

    games, selected_team, show_primetime_only = get_filtered_games(request, base_games)

    paginator = Paginator(games, 12)
    page_obj = paginator.get_page(request.GET.get('page', 1))

    context = {
        'games': page_obj,
        'teams': get_teams_dropdown(base_games),
        'selected_team': selected_team,
        'show_primetime_only': show_primetime_only,
        'total_games': len(base_games),
        'primetime_count': sum(1 for g in base_games if g.is_primetime),
        'completed_games': sum(1 for g in games if g.is_finished),
        'week_start': week_start,
        'week_end': week_end,
    }
    return render(request, 'schedule.html', context)


@login_required
def weekly_score_view(request):
    """Display weekly scores or full schedule based on 'week' param."""
    week_param = request.GET.get('week', 'current')

    if week_param == 'all':
        base_games = Game.objects.all().order_by('-start_time')
        week_start, week_end = None, None
    else:
        week_start, week_end = get_current_week_dates()
        base_games = Game.objects.filter(
            start_time__date__gte=week_start,
            start_time__date__lte=week_end,
        ).order_by('-start_time')

    games, selected_team, show_primetime_only = get_filtered_games(request, base_games)

    # Add helper flags
    for game in games:
        game.has_score = game.status in ['final', 'in_progress'] and (game.home_score is not None or game.away_score is not None)
        game.away_is_winner = game.winner == game.away_team if game.winner else False
        game.home_is_winner = game.winner == game.home_team if game.winner else False

    paginator = Paginator(games, 15)
    page_obj = paginator.get_page(request.GET.get('page', 1))

    context = {
        'games': page_obj,
        'teams': get_teams_dropdown(base_games),
        'selected_team': selected_team,
        'show_primetime_only': show_primetime_only,
        'total_games': len(base_games),
        'primetime_count': sum(1 for g in base_games if g.is_primetime),
        'completed_games': sum(1 for g in games if g.is_finished),
        'week_start': week_start,
        'week_end': week_end,
        'is_scores_page': True,
        'show_all_weeks': week_param == 'all',  # flag for template
    }
    return render(request, 'views_score.html', context)
