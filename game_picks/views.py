from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.utils import timezone

from nfl_schedule.models import NFLGame
from .models import GameSelection, UserRecord, League, LeagueCreationRequest, LeagueJoinRequest
from .forms import GameSelectionForm, LeagueCreationRequestForm, LeagueJoinRequestForm


@login_required(login_url='login')
def display_nfl_schedule(request):
    current_date = timezone.now().date()

    if request.method == 'POST':
        form = GameSelectionForm(request.POST)

        if form.is_valid():
            game = form.cleaned_data['game']
            existing_prediction = GameSelection.objects.filter(user=request.user, game=game).first()

            if existing_prediction:
                existing_prediction.predicted_winner = form.cleaned_data['predicted_winner']
                existing_prediction.save()
            else:
                prediction = form.save(commit=False)
                prediction.user = request.user
                prediction.save()

            return redirect('schedule')

    else:
        form = GameSelectionForm()

    games = NFLGame.objects.filter(date=current_date)
    predictions = GameSelection.objects.filter(user=request.user, game__in=games)

    context = {
        'games': games,
        'predictions': predictions,
        'form': form,
    }

    return render(request, 'nfl_schedule/schedule.html', context)


def standings(request):
    user_records = UserRecord.objects.order_by('-correct_predictions')
    return render(request, 'nfl_schedule/standings.html', {'user_records': user_records})


# ===== League Request Views =====

@login_required
def request_create_league(request):
    if request.method == 'POST':
        form = LeagueCreationRequestForm(request.POST)
        if form.is_valid():
            creation_request = form.save(commit=False)
            creation_request.user = request.user
            creation_request.save()
            messages.success(request, 'Your league creation request has been submitted.')
            return redirect('landing_page')
    else:
        form = LeagueCreationRequestForm()
    return render(request, 'game_picks/request_create_league.html', {'form': form})


@login_required
def request_join_league(request):
    if request.method == 'POST':
        form = LeagueJoinRequestForm(request.POST)
        if form.is_valid():
            join_request = form.save(commit=False)
            join_request.user = request.user
            join_request.save()
            messages.success(request, 'Your request to join the league has been submitted.')
            return redirect('landing_page')
    else:
        form = LeagueJoinRequestForm()
    return render(request, 'game_picks/request_join_league.html', {'form': form})


@staff_member_required
def admin_league_creation_requests(request):
    if request.method == 'POST':
        request_id = request.POST.get('request_id')
        action = request.POST.get('action')
        creation_request = LeagueCreationRequest.objects.get(id=request_id)

        if action == 'approve':
            League.objects.create(
                name=creation_request.name,
                description=creation_request.description
            )
            creation_request.delete()
            messages.success(request, f"League '{creation_request.name}' approved.")
        elif action == 'deny':
            creation_request.delete()
            messages.info(request, f"League '{creation_request.name}' denied.")
        return redirect('admin_league_creation_requests')

    pending_requests = LeagueCreationRequest.objects.all()
    return render(request, 'game_picks/admin_league_creation_requests.html', {'pending_requests': pending_requests})


@staff_member_required
def admin_league_join_requests(request):
    if request.method == 'POST':
        request_id = request.POST.get('request_id')
        action = request.POST.get('action')
        join_request = LeagueJoinRequest.objects.get(id=request_id)

        if action == 'approve':
            UserRecord.objects.create(
                user=join_request.user,
                league=join_request.league,
                correct_predictions=0,
                total_predictions=0
            )
            join_request.delete()
            messages.success(request, f"{join_request.user.username} added to {join_request.league.name}.")
        elif action == 'deny':
            join_request.delete()
            messages.info(request, f"{join_request.user.username}'s request denied.")
        return redirect('admin_league_join_requests')

    pending_join_requests = LeagueJoinRequest.objects.all()
    return render(request, 'game_picks/admin_league_join_requests.html', {'pending_join_requests': pending_join_requests})
