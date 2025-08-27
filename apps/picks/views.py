from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.core.paginator import Paginator
from datetime import timedelta, datetime

from apps.games.models import Game
from apps.leagues.models import League
from .models import Pick


@login_required(login_url='login')
def display_nfl_schedule(request):
    now = timezone.now()

    # Week boundaries (Monday to Sunday)
    week_start = now - timedelta(days=now.weekday())
    week_end = week_start + timedelta(days=7)

    # Optionally skip preseason games (before Sept 1)
    season_start = timezone.datetime(now.year, 9, 1, tzinfo=timezone.utc)

    all_week_games = Game.objects.filter(
        start_time__gte=week_start,
        start_time__lt=week_end,
        start_time__gte=season_start
    ).order_by('start_time')

    # Show all games for the week (not just primetime)
    games = list(all_week_games)

    # League filtering
    league_id = request.GET.get('league') or request.POST.get('league')
    league = League.objects.filter(id=league_id, is_approved=True, members=request.user).first() if league_id else None
    if league_id and not league:
        messages.error(request, "Invalid or unauthorized league selected.")
        return redirect('schedule')

    # User's existing picks
    user_picks = Pick.objects.filter(user=request.user, game__in=games, league=league)
    picks_dict = {
        pick.game_id: 'home' if pick.picked_team == pick.game.home_team else 'away'
        for pick in user_picks
    }

    # Handle form submission
    if request.method == 'POST':
        for game in games:
            pick_key = f'pick_{game.id}'
            user_pick = request.POST.get(pick_key)
            if not user_pick:
                continue

            if now >= game.start_time:
                messages.warning(request, f"Picks for {game.away_team} @ {game.home_team} are closed.")
                continue

            picked_team = game.home_team if user_pick == 'home' else game.away_team

            Pick.objects.update_or_create(
                user=request.user,
                game=game,
                league=league,
                defaults={'picked_team': picked_team}
            )
        messages.success(request, "Your picks have been saved.")
        return redirect('schedule')

    # Prep context for template
    games_with_info = []
    for game in games:
        started = now >= game.start_time
        games_with_info.append({
            'game': game,
            'user_pick': picks_dict.get(game.id),
            'started': started,
        })

    context = {
        'games_with_info': games_with_info,
        'league': league,
        'primetime_count': len(games),  # Optional: rename to total_games if needed
    }
    return render(request, 'picks/schedule.html', context)


@login_required(login_url='login')
def general_standings(request):
    from django.db.models import Count
    from django.contrib.auth import get_user_model

    User = get_user_model()

    user_stats = []
    users_with_picks = User.objects.filter(pick__isnull=False).distinct()

    for user in users_with_picks:
        total_picks = Pick.objects.filter(user=user).count()
        correct_picks = Pick.objects.filter(user=user, is_correct=True).count()
        accuracy = round((correct_picks / total_picks) * 100, 2) if total_picks > 0 else 0

        user_stats.append({
            'user': user,
            'total_predictions': total_picks,
            'correct_predictions': correct_picks,
            'accuracy': accuracy
        })

    user_stats.sort(key=lambda x: (x['correct_predictions'], x['accuracy']), reverse=True)

    paginator = Paginator(user_stats, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
    }
    return render(request, 'picks/general_standings.html', context)


@login_required(login_url='login')
def standings(request):
    league_id = request.GET.get('league')
    if not league_id:
        messages.error(request, "No league selected.")
        return redirect('schedule')

    league = League.objects.filter(id=league_id, members=request.user).first()
    if not league:
        messages.error(request, "Invalid or unauthorized league selected.")
        return redirect('schedule')

    league_stats = []
    league_members = league.members.all()

    for member in league_members:
        total_picks = Pick.objects.filter(user=member, league=league).count()
        correct_picks = Pick.objects.filter(user=member, league=league, is_correct=True).count()
        accuracy = round((correct_picks / total_picks) * 100, 2) if total_picks > 0 else 0

        league_stats.append({
            'user': member,
            'total_predictions': total_picks,
            'correct_predictions': correct_picks,
            'accuracy': accuracy
        })

    league_stats.sort(key=lambda x: (x['correct_predictions'], x['accuracy']), reverse=True)

    paginator = Paginator(league_stats, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'league': league,
        'page_obj': page_obj,
    }
    return render(request, 'picks/standings.html', context)
