from django.shortcuts import render, redirect, get_object_or_404
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
    leagues = League.objects.filter(is_approved=True).exclude(members=request.user)
    return render(request, 'game_picks/join_league.html', {'leagues': leagues})


@staff_member_required
def admin_league_creation_requests(request):
    pending_requests = LeagueCreationRequest.objects.filter(is_approved=False)
    if request.method == 'POST':
        req_id = request.POST.get('request_id')
        action = request.POST.get('action')
        req = LeagueCreationRequest.objects.get(id=req_id)
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
        req = LeagueJoinRequest.objects.get(id=req_id)
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


# New view: Show league details and standings, only if user is a member
@login_required
def league_detail(request, league_id):
    league = get_object_or_404(League, id=league_id, is_approved=True)

    if request.user not in league.members.all():
        messages.error(request, "You are not a member of this league.")
        return redirect('landing_page')

    user_records = UserRecord.objects.filter(league=league).order_by('-correct_predictions')
    
    # Calculate accuracy for each record
    for record in user_records:
        if record.total_predictions > 0:
            record.accuracy = round((record.correct_predictions / record.total_predictions) * 100, 2)
        else:
            record.accuracy = None

    context = {
        'league': league,
        'user_records': user_records,
    }
    return render(request, 'game_picks/league_detail.html', context)
