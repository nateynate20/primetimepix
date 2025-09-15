# apps/leagues/views.py - Complete version with all functions

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Sum, Count, Q
from django.core.mail import send_mail
from django.conf import settings

from .models import League, LeagueMembership, LeagueCreationRequest, LeagueJoinRequest
from .forms import LeagueCreationRequestForm, LeagueJoinRequestForm


def is_superadmin(user):
    """Check if user is superadmin"""
    return user.is_superuser


@login_required
def select_league(request):
    """Show user's leagues"""
    leagues = League.objects.filter(
        members=request.user
    ).annotate(
        member_count=Count('members')
    ).select_related('commissioner')
    
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
        league = get_object_or_404(League, id=league_id, is_approved=True)
        
        if league.members.filter(id=request.user.id).exists():
            messages.info(request, "You're already a member of this league.")
            return redirect('league_detail_no_id')
        
        if request.method == 'POST':
            if league.is_private:
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
            else:
                LeagueMembership.objects.get_or_create(user=request.user, league=league)
                messages.success(request, f"Successfully joined {league.name}!")
                return redirect('league_detail', league_id=league.id)
        
        return redirect('league_detail_no_id')
    
    # Original form-based logic
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
            league = League.objects.create(
                name=req.league_name,
                commissioner=req.user,
                description=getattr(req, 'description', '') or '',
                is_approved=True,
                is_private=True
            )
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
    ).order_by('-created_at')
    
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
    
    # Separate public and private leagues
    public_leagues = [l for l in leagues if not l.is_private]
    private_leagues = [l for l in leagues if l.is_private]
    
    context = {
        'leagues': leagues,
        'public_leagues': public_leagues,
        'private_leagues': private_leagues,
    }
    
    return render(request, 'league_list.html', context)


@login_required
def join_league_instant(request, league_id):
    """Instantly join a public league or request to join a private league"""
    if request.method != 'POST':
        return redirect('league_list')
        
    league = get_object_or_404(League, id=league_id, is_approved=True)
    
    # Check if already a member
    if league.members.filter(id=request.user.id).exists():
        messages.info(request, f"You're already a member of {league.name}.")
        return redirect('league_detail', league_id=league.id)
    
    if league.is_private:
        # Create join request for private league
        existing_request = LeagueJoinRequest.objects.filter(
            user=request.user,
            league=league,
            approved=False
        ).first()
        
        if existing_request:
            messages.info(request, f"You've already requested to join {league.name}.")
        else:
            LeagueJoinRequest.objects.create(user=request.user, league=league)
            messages.success(request, f"Join request sent for {league.name}. You'll be notified when approved.")
            
            # Send email notification to commissioner
            try:
                if league.commissioner.email:
                    send_mail(
                        f'New join request for {league.name}',
                        f'{request.user.username} has requested to join your league "{league.name}".\n\n'
                        f'Approve or deny this request at: {settings.SITE_URL}/leagues/my-requests/',
                        settings.DEFAULT_FROM_EMAIL,
                        [league.commissioner.email],
                        fail_silently=True,
                    )
            except Exception as e:
                print(f"Email notification failed: {e}")
    else:
        # Instantly join public league
        membership, created = LeagueMembership.objects.get_or_create(
            user=request.user,
            league=league
        )
        if created:
            messages.success(request, f"Successfully joined {league.name}!")
            
            # Optional: Send welcome email
            try:
                if request.user.email:
                    send_mail(
                        f'Welcome to {league.name}!',
                        f'You have successfully joined the league "{league.name}".\n\n'
                        f'Start making your picks at: {settings.SITE_URL}/picks/?league={league.id}',
                        settings.DEFAULT_FROM_EMAIL,
                        [request.user.email],
                        fail_silently=True,
                    )
            except Exception as e:
                print(f"Welcome email failed: {e}")
                
        return redirect('league_detail', league_id=league.id)
    
    return redirect('league_list')


@login_required
def create_league(request):
    """Create a new league (instant creation for verified users)"""
    if request.method == 'POST':
        # Get form data
        name = request.POST.get('name')
        description = request.POST.get('description', '')
        sport = request.POST.get('sport', 'NFL')
        is_private = request.POST.get('is_private') == 'on'
        
        # Validate
        if not name:
            messages.error(request, "League name is required.")
            return redirect('create_league')
        
        # Check for duplicate names
        if League.objects.filter(name=name).exists():
            messages.error(request, f"A league named '{name}' already exists.")
            return redirect('create_league')
        
        # Create the league instantly
        league = League.objects.create(
            name=name,
            commissioner=request.user,
            description=description,
            sport=sport,
            is_private=is_private,
            is_approved=True  # Auto-approve for now
        )
        
        messages.success(request, f"League '{name}' created successfully! You are now the commissioner.")
        
        # Send confirmation email
        try:
            if request.user.email:
                send_mail(
                    f'League Created: {league.name}',
                    f'Your league "{league.name}" has been created successfully!\n\n'
                    f'League Settings:\n'
                    f'- Type: {"Private" if is_private else "Public"}\n'
                    f'- Sport: {sport}\n\n'
                    f'Invite others to join at: {settings.SITE_URL}/leagues/{league.id}/',
                    settings.DEFAULT_FROM_EMAIL,
                    [request.user.email],
                    fail_silently=True,
                )
        except Exception as e:
            print(f"League creation email failed: {e}")
        
        return redirect('league_detail', league_id=league.id)
    
    # GET request - show form
    context = {
        'form': {
            'name': '',
            'description': '',
            'sport': 'NFL',
            'is_private': False,
        }
    }
    return render(request, 'create_league.html', context)


@login_required
def my_leagues(request):
    """Show all leagues where user is a member or commissioner"""
    # Get leagues where user is a member
    member_leagues = League.objects.filter(
        members=request.user,
        is_approved=True
    ).annotate(member_count=Count('members'))
    
    # Get leagues where user is commissioner
    commissioner_leagues = League.objects.filter(
        commissioner=request.user,
        is_approved=True
    ).annotate(member_count=Count('members'))
    
    # Get pending join requests for user's leagues
    pending_requests = LeagueJoinRequest.objects.filter(
        league__commissioner=request.user,
        approved=False
    ).select_related('user', 'league')
    
    context = {
        'member_leagues': member_leagues,
        'commissioner_leagues': commissioner_leagues,
        'pending_requests': pending_requests,
        'total_leagues': member_leagues.count(),
    }
    return render(request, 'leagues/my_leagues.html', context)


@login_required
def my_league_requests(request):
    """Show pending requests for leagues where user is commissioner"""
    pending_requests = LeagueJoinRequest.objects.filter(
        league__commissioner=request.user,
        approved=False
    ).select_related('user', 'league').order_by('-created_at')
    
    return render(request, 'pending_request.html', {
        'pending_requests': pending_requests
    })


@login_required
@require_POST
def approve_join_request(request, request_id):
    """Approve a join request"""
    join_request = get_object_or_404(
        LeagueJoinRequest, 
        id=request_id, 
        league__commissioner=request.user
    )
    
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
@require_POST
def deny_join_request(request, request_id):
    """Deny a join request"""
    join_request = get_object_or_404(
        LeagueJoinRequest, 
        id=request_id, 
        league__commissioner=request.user
    )
    
    username = join_request.user.username
    join_request.delete()
    messages.success(request, f"Denied join request from {username}")
    
    return redirect('my_league_requests')