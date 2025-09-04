# games/views.py

from datetime import timedelta
from django.utils import timezone
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from .models import Game


def get_current_week_dates():
    """Get the start and end dates for the current week (Monday to Sunday)."""
    today = timezone.now().date()
    days_since_monday = today.weekday()
    week_start = today - timedelta(days=days_since_monday)
    week_end = week_start + timedelta(days=6)
    return week_start, week_end


@login_required
def weekly_primetime_view(request):
    """View for displaying weekly primetime games with optional filters."""

    week_start, week_end = get_current_week_dates()

    # Base queryset for this week
    base_games = Game.objects.filter(
        start_time__date__gte=week_start,
        start_time__date__lte=week_end,
    ).order_by('start_time')

    # Optional team filter
    selected_team = request.GET.get('team')
    if selected_team:
        base_games = base_games.filter(
            models.Q(home_team__iexact=selected_team) |
            models.Q(away_team__iexact=selected_team)
        )

    # Check if user wants primetime only
    show_primetime_only = request.GET.get('primetime') == 'true'

    if show_primetime_only:
        games = [g for g in base_games if g.is_primetime]
    else:
        games = base_games

    # Pagination
    paginator = Paginator(games, 12)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    # Statistics
    total_games = base_games.count() if hasattr(base_games, 'count') else len(base_games)
    primetime_count = sum(1 for g in base_games if g.is_primetime)

    # Collect unique teams (for dropdown/filter UI)
    team_set = set()
    for g in Game.objects.filter(start_time__date__gte=week_start, start_time__date__lte=week_end):
        team_set.add(g.home_team)
        team_set.add(g.away_team)
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

    return render(request, 'views_score.html', context)


@login_required
def weekly_score_view(request):
    """View for displaying weekly scores."""

    week_start, week_end = get_current_week_dates()

    # Completed games for the week
    games = Game.objects.filter(
        start_time__date__gte=week_start,
        start_time__date__lte=week_end,
        status__in=['FINAL', 'COMPLETED', 'F', 'final', 'completed']
    ).order_by('-start_time')

    # If no completed games, show all games from this week
    if not games.exists():
        games = Game.objects.filter(
            start_time__date__gte=week_start,
            start_time__date__lte=week_end,
        ).order_by('-start_time')

    # Optional team filter
    selected_team = request.GET.get('team')
    if selected_team:
        games = games.filter(
            models.Q(home_team__iexact=selected_team) |
            models.Q(away_team__iexact=selected_team)
        )

    # Pagination
    paginator = Paginator(games, 12)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    # Stats
    total_games = games.count()
    completed_games = Game.objects.filter(
        start_time__date__gte=week_start,
        start_time__date__lte=week_end,
        status__in=['FINAL', 'COMPLETED', 'F', 'final', 'completed']
    ).count()

    # Collect unique teams for dropdown/filter
    team_set = set()
    for g in Game.objects.filter(start_time__date__gte=week_start, start_time__date__lte=week_end):
        team_set.add(g.home_team)
        team_set.add(g.away_team)
    teams = sorted(team_set)

    context = {
        'games': page_obj,
        'teams': teams,
        'selected_team': selected_team,
        'total_games': total_games,
        'completed_games': completed_games,
        'week_start': week_start,
        'week_end': week_end,
    }

    return render(request, 'views_score.html', context)
