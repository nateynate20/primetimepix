# apps/leagues/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Sum, Count, Q

from .models import League, LeagueMembership, LeagueCreationRequest, LeagueJoinRequest
from .forms import LeagueCreationRequestForm, LeagueJoinRequestForm

# Only superusers should see creation/join requests for now
def is_superadmin(user):
    return user.is_superuser

@login_required
def select_league(request):
    # Use annotation to calculate member_count in the database
    # This avoids the property setter conflict
    leagues = League.objects.filter(
        members=request.user
    ).annotate(
        member_count=Count('members')
    ).select_related('commissioner')  # Optional: optimize commissioner queries
    
    context = {
        'leagues': leagues,
    }
    return render(request, 'select_league.html', context)

@login_required
def league_detail(request, league_id):
    """Show league details and standings"""
    league = get_object_or_404(League, id=league_id, is_approved=True)
    
    # Check if user is a member
    if not league.members.filter(id=request.user.id).exists():
        messages.error(request, "You are not a member of this league.")
        return redirect('league_detail_no_id')
    
    # Get league standings using the model method
    standings = league.get_standings()
    
    # Paginate standings
    paginator = Paginator(standings, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'league': league,
        'page_obj': page_obj,
        'user': request.user,
        'total_members': league.members.count(),
    }
    return render(request, 'league_detail.html', context)

@login_required
def request_create_league(request):
    """Submit a request to create a new league"""
    if request.method == 'POST':
        form = LeagueCreationRequestForm(request.POST)
        if form.is_valid():
            # Check if user already has a pending request
            existing_request = LeagueCreationRequest.objects.filter(
                user=request.user, 
                approved=False
            ).first()
            
            if existing_request:
                messages.warning(request, f'You already have a pending request for "{existing_request.league_name}". Please wait for approval.')
                return redirect('league_detail_no_id')
            
            obj = form.save(commit=False)
            obj.user = request.user
            obj.save()
            messages.success(request, '✅ Your league creation request has been submitted for approval.')
            return redirect('league_detail_no_id')
    else:
        form = LeagueCreationRequestForm()
    
    context = {
        'form': form,
        'user': request.user,
    }
    return render(request, 'league_create_request.html', context)

@login_required
def request_join_league(request, league_id=None):
    """Handle both public league joins and private league join requests"""
    if league_id:
        # Direct league join/request from league list
        league = get_object_or_404(League, id=league_id, is_approved=True)
        
        # Check if user is already a member
        if league.members.filter(id=request.user.id).exists():
            messages.info(request, "You're already a member of this league.")
            return redirect('league_detail_no_id')
        
        if request.method == 'POST':
            if league.is_private:
                # Create join request for private league
                existing_request = LeagueJoinRequest.objects.filter(
                    user=request.user, 
                    league=league, 
                    approved=False
                ).first()
                
                if existing_request:
                    messages.info(request, "You've already requested to join this league.")
                else:
                    LeagueJoinRequest.objects.create(user=request.user, league=league)
                    messages.success(request, f"Join request sent for {league.name}. You'll be notified when approved.")
                    
                    # Send email to commissioner if they have email
                    if league.commissioner.email:
                        try:
                            from django.core.mail import send_mail
                            from django.conf import settings
                            send_mail(
                                f'New join request for {league.name}',
                                f'{request.user.username} has requested to join your league "{league.name}".\n\nApprove this request in the admin panel: {request.build_absolute_uri("/admin/")}',
                                settings.DEFAULT_FROM_EMAIL,
                                [league.commissioner.email],
                                fail_silently=True,
                            )
                        except Exception as e:
                            print(f"Email notification failed: {e}")
            else:
                # Join public league directly
                LeagueMembership.objects.get_or_create(user=request.user, league=league)
                messages.success(request, f"Successfully joined {league.name}!")
                return redirect('league_detail', league_id=league.id)
        
        return redirect('league_detail_no_id')
    
    # Original form-based logic for general join requests
    if request.method == 'POST':
        form = LeagueJoinRequestForm(request.POST, user=request.user)
        if form.is_valid():
            league = form.cleaned_data['league']
            
            if league.members.filter(id=request.user.id).exists():
                messages.warning(request, 'You are already a member of this league.')
                return redirect('league_detail_no_id')
            
            if LeagueJoinRequest.objects.filter(user=request.user, league=league).exists():
                messages.warning(request, 'You have already requested to join this league.')
                return redirect('league_detail_no_id')
            
            obj = form.save(commit=False)
            obj.user = request.user
            obj.save()
            messages.success(request, f'Your request to join "{league.name}" has been submitted.')
            return redirect('league_detail_no_id')
    else:
        form = LeagueJoinRequestForm(user=request.user)
    
    available_leagues = League.objects.filter(
        is_approved=True,
        is_private=False
    ).exclude(members=request.user).order_by('name')
    
    context = {
        'form': form,
        'user': request.user,
        'available_leagues': available_leagues,
    }
    return render(request, 'league_join_request.html', context)

@user_passes_test(is_superadmin)
def review_league_creation_requests(request):
    """Admin view to review league creation requests"""
    if request.method == 'POST':
        req_id = request.POST.get('request_id')
        action = request.POST.get('action')
        req = get_object_or_404(LeagueCreationRequest, id=req_id)
        
        if action == 'approve':
            # Create the actual league
            league = League.objects.create(
                name=req.league_name,
                commissioner=req.user,
                description=getattr(req, 'description', '') or '',
                is_approved=True,
                is_private=True
            )
            # Mark request as approved
            req.approved = True
            req.save()
            messages.success(request, f"✅ Created and approved league: {req.league_name}")
        elif action == 'deny':
            req.delete()
            messages.warning(request, f"❌ Denied and deleted league creation request: {req.league_name}")
        
        return redirect('creation_requests_list')

    pending_requests = LeagueCreationRequest.objects.filter(approved=False).order_by('-created_at')
    
    context = {
        'pending_requests': pending_requests,
    }
    return render(request, 'admins/league_creation_requests.html', context)

@user_passes_test(is_superadmin)
def review_league_join_requests(request):
    """Admin view to review league join requests"""
    if request.method == 'POST':
        req_id = request.POST.get('request_id')
        action = request.POST.get('action')
        req = get_object_or_404(LeagueJoinRequest, id=req_id)

        if action == 'approve':
            # Add user to league
            LeagueMembership.objects.get_or_create(
                user=req.user,
                league=req.league
            )
            req.approved = True
            req.save()
            messages.success(request, f"✅ Approved join request for {req.user.username} to {req.league.name}")
        elif action == 'deny':
            req.delete()
            messages.warning(request, f"❌ Denied join request for {req.user.username} to {req.league.name}")
        
        return redirect('join_requests_list')

    pending_join_requests = LeagueJoinRequest.objects.filter(approved=False).order_by('-created_at')
    
    context = {
        'pending_join_requests': pending_join_requests,
    }
    return render(request, 'admins/league_join_requests.html', context)

def league_list(request):
    """Show all approved leagues (both public and private)"""
    leagues = League.objects.filter(is_approved=True).select_related('commissioner').annotate(
        member_count=Count('members')
    )
    
    # Add membership status for each league
    for league in leagues:
        if request.user.is_authenticated:
            league.user_is_member = request.user in league.members.all()
            league.has_pending_request = LeagueJoinRequest.objects.filter(
                user=request.user,
                league=league,
                approved=False
            ).exists()
        else:
            league.user_is_member = False
            league.has_pending_request = False
    
    return render(request, 'leagues/league_list.html', {'leagues': leagues})

@login_required
def my_league_requests(request):
    """Show pending requests for leagues where user is commissioner"""
    pending_requests = LeagueJoinRequest.objects.filter(
        league__commissioner=request.user,
        approved=False
    ).select_related('user', 'league').order_by('-created_at')
    
    return render(request, 'leagues/pending_requests.html', {
        'pending_requests': pending_requests
    })

@login_required
def approve_join_request(request, request_id):
    """Approve a join request"""
    join_request = get_object_or_404(
        LeagueJoinRequest, 
        id=request_id, 
        league__commissioner=request.user
    )
    
    if request.method == 'POST':
        LeagueMembership.objects.get_or_create(
            user=join_request.user,
            league=join_request.league
        )
        
        join_request.approved = True
        join_request.save()
        
        messages.success(request, f"Approved {join_request.user.username} to join {join_request.league.name}")
        
        # Send approval email
        if join_request.user.email:
            try:
                from django.core.mail import send_mail
                from django.conf import settings
                send_mail(
                    f'Welcome to {join_request.league.name}!',
                    f'Your request to join "{join_request.league.name}" has been approved! You can now make picks and compete with other members.',
                    settings.DEFAULT_FROM_EMAIL,
                    [join_request.user.email],
                    fail_silently=True,
                )
            except Exception as e:
                print(f"Approval email failed: {e}")
    
    return redirect('my_league_requests')

@login_required
def deny_join_request(request, request_id):
    """Deny a join request"""
    join_request = get_object_or_404(
        LeagueJoinRequest, 
        id=request_id, 
        league__commissioner=request.user
    )
    
    if request.method == 'POST':
        username = join_request.user.username
        join_request.delete()
        messages.success(request, f"Denied join request from {username}")
    
    return redirect('my_league_requests')