from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from .forms import LeagueCreationRequestForm, LeagueJoinRequestForm
from .models import LeagueCreationRequest, LeagueJoinRequest, League

@login_required
def request_league_creation(request):
    if request.method == 'POST':
        form = LeagueCreationRequestForm(request.POST)
        if form.is_valid():
            league_request = form.save(commit=False)
            league_request.user = request.user
            league_request.save()
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
            join_request.save()
            return redirect('landing_page')
    else:
        form = LeagueJoinRequestForm(user=request.user)
    return render(request, 'league_join_request.html', {'form': form})

@staff_member_required
def admin_league_requests(request):
    pending_requests = LeagueCreationRequest.objects.filter(is_approved=False)
    if request.method == 'POST':
        req_id = request.POST.get('request_id')
        action = request.POST.get('action')
        req = LeagueCreationRequest.objects.get(id=req_id)
        if action == 'approve':
            league = League.objects.create(
                name=req.name,
                description=req.description,
                is_approved=True
            )
            league.members.add(req.user)
            req.is_approved = True
            req.save()
        elif action == 'deny':
            req.delete()
        return redirect('admin_league_requests')
    return render(request, 'admins/league_creation_requests.html', {'pending_requests': pending_requests})

@staff_member_required
def admin_league_join_requests(request):
    pending_join_requests = LeagueJoinRequest.objects.filter(is_approved=False)
    if request.method == 'POST':
        req_id = request.POST.get('request_id')
        action = request.POST.get('action')
        req = LeagueJoinRequest.objects.get(id=req_id)
        if action == 'approve':
            req.league.members.add(req.user)
            req.is_approved = True
            req.save()
        elif action == 'deny':
            req.delete()
        return redirect('admin_league_join_requests')
    return render(request, 'admins/league_join_requests.html', {'pending_join_requests': pending_join_requests})
