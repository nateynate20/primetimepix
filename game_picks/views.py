from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.utils import timezone
from django.core.paginator import Paginator
from django.db.models import Q
from datetime import timedelta, datetime

from nfl_schedule.models import NFLGame
from .models import (
    GameSelection, UserRecord, League,
    LeagueCreationRequest, LeagueJoinRequest
)
from .forms import LeagueCreationRequestForm, LeagueJoinRequestForm


@login_required(login_url='login')
def display_nfl_schedule(request):
    now = timezone.now()

    # Calculate current week start (Monday) and end (Sunday)
    week_start = now - timedelta(days=now.weekday())
    week_end = week_start + timedelta(days=7)

    # Filter games for current week
    games = NFLGame.objects.filter(date__gte=week_start.date(), date__lt=week_end.date()).order_by('date', 'start_time')

    # Get user's picks for these games
    user_picks = GameSelection.objects.filter(user=request.user, game__in=games)
    picks_dict = {pick.game_id: pick.predicted_winner for pick in user_picks}

    if request.method == 'POST':
        # Save submitted picks
        for game in games:
            pick_key = f'pick_{game.id}'
            user_pick = request.POST.get(pick_key)
            if user_pick:
                # Check if game has started
                game_datetime = datetime.combine(game.date, game.start_time)
                game_datetime = timezone.make_aware(game_datetime, timezone.get_current_timezone())

                if now >= game_datetime:
                    messages.warning(request, f"Picks for {game.away_team} @ {game.home_team} are closed because the game started.")
                    continue

                # Save or update pick
                GameSelection.objects.update_or_create(
                    user=request.user,
                    game=game,
                    defaults={'predicted_winner': user_pick}
                )
        messages.success(request, "Your picks have been saved.")
        return redirect('schedule')

    # Prepare games with user's picks and if game started flag
    games_with_info = []
    for game in games:
        game_datetime = datetime.combine(game.date, game.start_time)
        game_datetime = timezone.make_aware(game_datetime, timezone.get_current_timezone())
        started = now >= game_datetime

        games_with_info.append({
            'game': game,
            'user_pick': picks_dict.get(game.id),
            'started': started,
        })

    context = {
        'games_with_info': games_with_info,
    }
    return render(request, 'schedule.html', context)


@login_required
def request_create_league(request):
    if request.method == 'POST':
        form = LeagueCreationRequestForm(request.POST)
        if form.is_valid():
            league_request = form.save(commit=False)
            league_request.user = request.user
            league_request.is_approved = True
            league_request.reviewed_at = timezone.now()
            league_request.reviewed_by = request.user
            league_request.save()

            league = League.objects.create(
                name=league_request.name,
                description=league_request.description,
                is_approved=True,
                created_by=request.user,
            )
            league.members.add(request.user)

            messages.success(request, "League created and approved successfully!")
            return redirect('landing_page')
    else:
        form = LeagueCreationRequestForm()

    return render(request, 'league_create_request.html', {'form': form})


@login_required
def request_join_league(request):
    if request.method == 'POST':
        form = LeagueJoinRequestForm(request.POST, user=request.user)
        if form.is_valid():
            join_request = form.save(commit=False)
            join_request.user = request.user
            join_request.is_approved = True
            join_request.reviewed_at = timezone.now()
            join_request.reviewed_by = request.user
            join_request.save()

            join_request.league.members.add(request.user)
            messages.success(request, f"You have successfully joined {join_request.league.name}.")
            return redirect('landing_page')
    else:
        form = LeagueJoinRequestForm(user=request.user)

    return render(request, 'league_join_request.html', {'form': form})


@login_required
def join_league_view(request):
    # Leagues user is NOT part of, to join
    leagues = League.objects.filter(is_approved=True).exclude(members=request.user)
    return render(request, 'select_league.html', {'leagues': leagues})


@staff_member_required
def admin_league_creation_requests(request):
    pending_requests = LeagueCreationRequest.objects.filter(is_approved=False)
    if request.method == 'POST':
        req_id = request.POST.get('request_id')
        action = request.POST.get('action')
        req = get_object_or_404(LeagueCreationRequest, id=req_id)
        if action == 'approve':
            league = League.objects.create(
                name=req.name,
                description=req.description,
                is_approved=True,
                created_by=req.user
            )
            league.members.add(req.user)
            req.is_approved = True
            req.reviewed_at = timezone.now()
            req.reviewed_by = request.user
            req.save()
        elif action == 'deny':
            req.delete()
        return redirect('admin_league_creation_requests')

    return render(request, 'admins/league_creation_requests.html', {'pending_requests': pending_requests})


@staff_member_required
def admin_league_join_requests(request):
    pending_requests = LeagueJoinRequest.objects.filter(is_approved=False)
    if request.method == 'POST':
        req_id = request.POST.get('request_id')
        action = request.POST.get('action')
        req = get_object_or_404(LeagueJoinRequest, id=req_id)
        if action == 'approve':
            req.league.members.add(req.user)
            req.is_approved = True
            req.reviewed_at = timezone.now()
            req.reviewed_by = request.user
            req.save()
        elif action == 'deny':
            req.delete()
        return redirect('admin_league_join_requests')

    return render(request, 'admins/league_join_requests.html', {'pending_requests': pending_requests})


@login_required
def league_detail(request, league_id=None):
    """
    If league_id is None, and user belongs to multiple leagues,
    redirect to a page for user to select which league's standings to view.
    If league_id is provided, show that league's standings.
    """
    user_leagues = League.objects.filter(members=request.user, is_approved=True)

    if league_id is None:
        if user_leagues.count() == 0:
            messages.error(request, "You are not a member of any league.")
            return redirect('landing_page')
        elif user_leagues.count() == 1:
            # Only one league, redirect directly
            return redirect('league_detail', league_id=user_leagues.first().id)
        else:
            # Multiple leagues, ask user to select
            return render(request, 'select_league.html', {'leagues': user_leagues})

    league = get_object_or_404(League, id=league_id, is_approved=True)

    if request.user not in league.members.all():
        messages.error(request, "You are not a member of this league.")
        return redirect('landing_page')

    _update_league_user_records(league)

    standings = UserRecord.objects.filter(league=league).order_by('-correct_predictions')

    paginator = Paginator(standings, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'league': league,
        'page_obj': page_obj,
    }
    return render(request, 'league_detail.html', context)


@login_required
def general_standings(request):
    _update_league_user_records()  # Update all records globally
    standings = UserRecord.objects.order_by('-correct_predictions')

    paginator = Paginator(standings, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'general_standings.html', {'page_obj': page_obj})


# 🔁 Shared logic to update user records (for general + league)
def _update_league_user_records(league=None):
    selections = GameSelection.objects.select_related('game', 'user')

    if league:
        selections = selections.filter(league=league)

    user_stats = {}

    for selection in selections:
        game = selection.game
        if game.home_score is None or game.away_score is None:
            continue

        actual_winner = 'home' if game.home_score > game.away_score else (
            'away' if game.away_score > game.home_score else None
        )
        if not actual_winner:
            continue

        user = selection.user
        user_pick = selection.predicted_winner

        key = (user, selection.league)
        if key not in user_stats:
            user_stats[key] = {'correct': 0, 'total': 0}

        user_stats[key]['total'] += 1
        if user_pick == actual_winner:
            user_stats[key]['correct'] += 1

    for (user, league_obj), stats in user_stats.items():
        correct = stats['correct']
        total = stats['total']
        accuracy = round((correct / total) * 100, 2) if total else 0

        record, _ = UserRecord.objects.get_or_create(user=user, league=league_obj)
        record.correct_predictions = correct
        record.total_predictions = total
        record.accuracy = accuracy
        record.save()
