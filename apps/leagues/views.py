# apps/leagues/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.http import require_POST
from django.contrib import messages

from .models import League, LeagueMembership, LeagueCreationRequest, LeagueJoinRequest
from .forms import LeagueCreationRequestForm, LeagueJoinRequestForm

# Only superusers should see creation/join requests for now
def is_superadmin(user):
    return user.is_superuser

@login_required
def select_league(request):
    leagues = request.user.leagues.all()
    return render(request, 'select_league.html', {'leagues': leagues})

@login_required
def league_detail(request, league_id):
    league = get_object_or_404(League, id=league_id)
    # Add logic here to compute standings if needed
    return render(request, 'league_detail.html', {'league': league})

@login_required
def request_create_league(request):
    if request.method == 'POST':
        form = LeagueCreationRequestForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.user = request.user
            obj.save()
            messages.success(request, '✅ Your league creation request has been submitted.')
            return redirect('select_league')
    else:
        form = LeagueCreationRequestForm()
    return render(request, 'league_create_request.html', {'form': form})

@user_passes_test(is_superadmin)
def review_league_creation_requests(request):
    if request.method == 'POST':
        req_id = request.POST.get('request_id')
        action = request.POST.get('action')
        req = get_object_or_404(LeagueCreationRequest, id=req_id)
        if action == 'approve':
            req.approved = True
            req.save()
            messages.success(request, f"✅ Approved league creation: {req.league_name}")
        elif action == 'deny':
            req.delete()
            messages.warning(request, f"❌ Denied and deleted league creation request: {req.league_name}")
        return redirect('review_league_creation_requests')

    pending_requests = LeagueCreationRequest.objects.filter(approved=False)
    return render(request, 'admins/league_creation_requests.html', {
        'pending_requests': pending_requests
    })

@login_required
def request_join_league(request, league_id=None):
    if request.method == 'POST':
        form = LeagueJoinRequestForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.user = request.user
            obj.save()
            messages.success(request, '✅ Your request to join the league has been submitted.')
            return redirect('select_league')
    else:
        form = LeagueJoinRequestForm(initial={'league': league_id} if league_id else {})
    return render(request, 'league_join_request.html', {'form': form})

@user_passes_test(is_superadmin)
def review_league_join_requests(request):
    if request.method == 'POST':
        req_id = request.POST.get('request_id')
        action = request.POST.get('action')
        req = get_object_or_404(LeagueJoinRequest, id=req_id)

        if action == 'approve':
            LeagueMembership.objects.create(user=req.user, league=req.league)
            req.approved = True
            req.save()
            messages.success(request, f"✅ Approved join request for {req.user.username} to {req.league.name}")
        elif action == 'deny':
            req.delete()
            messages.warning(request, f"❌ Denied join request for {req.user.username} to {req.league.name}")
        return redirect('review_league_join_requests')

    pending_join_requests = LeagueJoinRequest.objects.filter(approved=False)
    return render(request, 'admins/league_join_requests.html', {
        'pending_join_requests': pending_join_requests
    })
