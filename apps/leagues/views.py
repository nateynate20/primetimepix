# apps/leagues/views.py - Complete version with all functions

from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Sum, Count, Q
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string

from .models import League, LeagueMembership, LeagueCreationRequest, LeagueJoinRequest
from .forms import LeagueCreationRequestForm, LeagueJoinRequestForm, LeagueEditForm

User = get_user_model()


def is_superadmin(user):
    """Check if user is superadmin"""
    return user.is_superuser


def get_commissioner_league_or_404(league_id, user):
    """Return the league only if the user is a commissioner or co-commissioner."""
    league = get_object_or_404(League, id=league_id)
    if not league.is_commissioner(user):
        from django.http import Http404
        raise Http404("You do not manage this league.")
    return league


@login_required
def select_league(request):
    """Show user's leagues"""
    leagues = League.objects.filter(
        members=request.user
    ).annotate(
        member_count=Count('members')
    ).select_related('commissioner')

    total_members = sum(l.member_count for l in leagues)

    # Public leagues the user can join instantly.
    available_leagues = League.objects.filter(
        is_approved=True,
        is_private=False
    ).exclude(members=request.user).annotate(
        member_count=Count('members')
    ).order_by('name')

    # Private leagues the user can request to join. Previously these were hidden
    # entirely, so private leagues looked invisible on the join page — surface
    # them with a "request to join" action, flagging any already-pending ones.
    available_private = League.objects.filter(
        is_approved=True,
        is_private=True
    ).exclude(members=request.user).annotate(
        member_count=Count('members')
    ).order_by('name')
    pending_ids = set(
        LeagueJoinRequest.objects.filter(
            user=request.user, approved=False
        ).values_list('league_id', flat=True)
    )
    for lg in available_private:
        lg.has_pending_request = lg.id in pending_ids

    context = {
        'leagues': leagues,
        'total_members': total_members,
        'available_leagues': available_leagues,
        'available_private': available_private,
    }
    return render(request, 'select_league.html', context)


@login_required
def league_detail(request, league_id):
    """Show league details and standings"""
    league = get_object_or_404(League, id=league_id, is_approved=True)

    # Non-members get a preview with a way to join/request — not a blank
    # redirect. This is what people land on when they open a shared or private
    # league link they aren't in yet, so "you can't see anything" is fixed for
    # both public and private leagues.
    if not league.members.filter(id=request.user.id).exists():
        has_pending_request = LeagueJoinRequest.objects.filter(
            user=request.user, league=league, approved=False
        ).exists()
        return render(request, 'league_preview.html', {
            'league': league,
            'member_count': league.members.count(),
            'join_locked': league.is_join_locked(),
            'has_pending_request': has_pending_request,
        })
    
    # Get league standings using the model method
    standings = league.get_standings()
    
    # Paginate standings
    paginator = Paginator(standings, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    from apps.games.utils import get_current_nfl_week

    context = {
        'league': league,
        'page_obj': page_obj,
        'user': request.user,
        'total_members': league.members.count(),
        'current_week': get_current_nfl_week(),
        'is_manager': league.is_commissioner(request.user),
        'co_commissioners': league.co_commissioners.all(),
        'join_locked': league.is_join_locked(),
        'invite_url': f"{settings.SITE_URL}{reverse('join_via_invite', args=[league.join_code])}",
        'public_standings_url': f"{settings.SITE_URL}{reverse('public_standings', args=[league.join_code])}",
    }
    return render(request, 'league_detail.html', context)


def public_standings(request, code):
    """Public, read-only league standings — no login required.

    Keyed by the league's invite code so the URL doubles as a shareable link
    (only people the code is shared with can find it). Renders the leaderboard
    plus a join / sign-up CTA, which closes the viral loop from the in-app
    "Share Standings" button and gives shared links something rich to preview.
    """
    league = get_object_or_404(League, join_code=code.upper(), is_approved=True)

    standings = league.get_standings()
    for idx, row in enumerate(standings, start=1):
        row['rank'] = idx

    from apps.games.utils import get_current_nfl_week

    is_member = (
        request.user.is_authenticated
        and league.members.filter(id=request.user.id).exists()
    )

    context = {
        'league': league,
        'standings': standings[:50],
        'total_members': league.members.count(),
        'current_week': get_current_nfl_week(),
        'join_locked': league.is_join_locked(),
        'is_member': is_member,
        'invite_url': f"{settings.SITE_URL}{reverse('join_via_invite', args=[league.join_code])}",
    }
    return render(request, 'leagues/public_standings.html', context)


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

        if league.is_join_locked():
            messages.error(request, f"{league.name} is locked — the season has already started, so new members can't join.")
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

            if league.is_join_locked():
                messages.error(request, f"{league.name} is locked — the season has already started, so new members can't join.")
                return redirect('league_detail_no_id')

            # Public leagues: instant join, no approval needed
            if not league.is_private:
                from apps.leagues.models import LeagueMembership
                LeagueMembership.objects.get_or_create(user=request.user, league=league)
                messages.success(request, f'Successfully joined {league.name}!')
                return redirect('league_detail', league_id=league.id)

            # Private leagues: create a join request for commissioner approval
            if LeagueJoinRequest.objects.filter(user=request.user, league=league).exists():
                messages.warning(request, 'You have already requested to join this league.')
                return redirect('league_detail_no_id')

            obj = form.save(commit=False)
            obj.user = request.user
            obj.save()
            messages.success(request, f'Your request to join "{league.name}" has been submitted for approval.')
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
                is_private=False
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

    if league.is_join_locked():
        messages.error(request, f"{league.name} is locked — the season has already started, so new members can't join.")
        return redirect('league_list')

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
            
            # Send email notification to all commissioners (primary + co-commissioners)
            try:
                commissioner_emails = [
                    c.email for c in league.all_commissioners() if c.email
                ]
                if commissioner_emails:
                    send_mail(
                        f'New join request for {league.name}',
                        f'{request.user.username} has requested to join your league "{league.name}".\n\n'
                        f'Approve or deny this request at: {settings.SITE_URL}/leagues/my-requests/',
                        settings.DEFAULT_FROM_EMAIL,
                        commissioner_emails,
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
            
            # Send welcome email
            try:
                if request.user.email:
                    html_message = render_to_string('emails/league_joined.html', {
                        'username': request.user.username,
                        'league_name': league.name,
                        'site_url': settings.SITE_URL,
                    })
                    send_mail(
                        f'Welcome to {league.name}!',
                        f'You have joined "{league.name}". Make picks at: {settings.SITE_URL}/picks/',
                        settings.DEFAULT_FROM_EMAIL,
                        [request.user.email],
                        html_message=html_message,
                        fail_silently=True,
                    )
            except Exception as e:
                print(f"Welcome email failed: {e}")
                
        return redirect('league_detail', league_id=league.id)
    
    return redirect('league_list')


@login_required
def create_league(request):
    """Instant league creation — staff only.

    Regular members go through the review/approval flow instead. The navbar and
    dashboard already route non-staff to that request flow; this guard closes
    the gap where someone could hit /leagues/create/ directly and bypass it, so
    there's one consistent 'create a league' experience for everyone.
    """
    from .forms import LeagueCreateForm

    if not request.user.is_staff:
        messages.info(request, "New leagues need a quick approval. Submit your request below and we'll get it set up.")
        return redirect('league_create_request')

    if request.method == 'POST':
        form = LeagueCreateForm(request.POST)
        if form.is_valid():
            league = form.save(commit=False)
            league.commissioner = request.user
            league.is_approved = True
            league.save()

            messages.success(request, f"League '{league.name}' created successfully! You are now the commissioner.")

            try:
                if request.user.email:
                    html_message = render_to_string('emails/league_created.html', {
                        'username': request.user.username,
                        'league_name': league.name,
                        'league_type': 'Private' if league.is_private else 'Public',
                        'league_sport': league.sport,
                        'site_url': settings.SITE_URL,
                    })
                    send_mail(
                        f'League Created: {league.name}',
                        f'Your league "{league.name}" has been created! View it at: {settings.SITE_URL}/leagues/league/{league.id}/',
                        settings.DEFAULT_FROM_EMAIL,
                        [request.user.email],
                        html_message=html_message,
                        fail_silently=True,
                    )
            except Exception as e:
                print(f"League creation email failed: {e}")

            return redirect('league_detail', league_id=league.id)
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = LeagueCreateForm()

    return render(request, 'create_league.html', {'form': form})


@login_required
def my_leagues(request):
    """Show all leagues where user is a member or commissioner"""
    from django.db.models import Sum

    member_leagues = League.objects.filter(
        members=request.user,
        is_approved=True
    ).annotate(member_count=Count('members')).distinct()

    commissioner_leagues = League.objects.filter(
        Q(commissioner=request.user) | Q(co_commissioners=request.user),
        is_approved=True
    ).annotate(member_count=Count('members')).distinct()

    pending_requests = LeagueJoinRequest.objects.filter(
        Q(league__commissioner=request.user) | Q(league__co_commissioners=request.user),
        approved=False
    ).select_related('user', 'league').distinct()

    # Combine all unique leagues for stats
    all_leagues = (member_leagues | commissioner_leagues).distinct()
    total_members = sum(l.member_count for l in all_leagues)

    context = {
        'member_leagues': member_leagues,
        'commissioner_leagues': commissioner_leagues,
        'pending_requests': pending_requests,
        'total_leagues': all_leagues.count(),
        'total_members': total_members,
        'active_leagues': all_leagues.count(),
    }
    return render(request, 'leagues/my_leagues.html', context)


@login_required
def my_league_requests(request):
    """Show pending requests for leagues where user is commissioner"""
    pending_requests = LeagueJoinRequest.objects.filter(
        Q(league__commissioner=request.user) | Q(league__co_commissioners=request.user),
        approved=False
    ).select_related('user', 'league').distinct().order_by('-created_at')
    
    return render(request, 'pending_request.html', {
        'pending_requests': pending_requests
    })


@login_required
@require_POST
def approve_join_request(request, request_id):
    """Approve a join request"""
    join_request = get_object_or_404(
        LeagueJoinRequest.objects.filter(
            Q(league__commissioner=request.user) | Q(league__co_commissioners=request.user)
        ).distinct(),
        id=request_id,
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
            html_message = render_to_string('emails/league_joined.html', {
                'username': join_request.user.username,
                'league_name': join_request.league.name,
                'site_url': settings.SITE_URL,
            })
            send_mail(
                f'Welcome to {join_request.league.name}!',
                f'Your request to join "{join_request.league.name}" has been approved! Make picks at: {settings.SITE_URL}/picks/',
                settings.DEFAULT_FROM_EMAIL,
                [join_request.user.email],
                html_message=html_message,
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
        LeagueJoinRequest.objects.filter(
            Q(league__commissioner=request.user) | Q(league__co_commissioners=request.user)
        ).distinct(),
        id=request_id,
    )
    
    username = join_request.user.username
    join_request.delete()
    messages.success(request, f"Denied join request from {username}")
    
    return redirect('my_league_requests')


# --------------------------------------
# League management (commissioners + co-commissioners)
# --------------------------------------
@login_required
def manage_league(request, league_id):
    """League management page for commissioners and co-commissioners."""
    league = get_commissioner_league_or_404(league_id, request.user)

    if request.method == 'POST':
        form = LeagueEditForm(request.POST, instance=league)
        if form.is_valid():
            form.save()
            messages.success(request, "League details updated.")
            return redirect('manage_league', league_id=league.id)
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = LeagueEditForm(instance=league)

    members = league.members.all().order_by('username')
    co_commissioner_ids = set(league.co_commissioners.values_list('id', flat=True))

    invite_url = f"{settings.SITE_URL}{reverse('join_via_invite', args=[league.join_code])}"

    context = {
        'league': league,
        'form': form,
        'members': members,
        'co_commissioner_ids': co_commissioner_ids,
        'invite_url': invite_url,
        'pending_requests': LeagueJoinRequest.objects.filter(
            league=league, approved=False
        ).select_related('user'),
    }
    return render(request, 'leagues/manage_league.html', context)


@login_required
@require_POST
def regenerate_invite(request, league_id):
    """Rotate a league's shareable invite code."""
    league = get_commissioner_league_or_404(league_id, request.user)
    league.regenerate_join_code()
    messages.success(request, "Invite link regenerated. The old link no longer works.")
    return redirect('manage_league', league_id=league.id)


@login_required
@require_POST
def remove_member(request, league_id, user_id):
    """Remove a member from a league (commissioners/co-commissioners only)."""
    league = get_commissioner_league_or_404(league_id, request.user)

    if user_id == league.commissioner_id:
        messages.error(request, "The primary commissioner cannot be removed.")
        return redirect('manage_league', league_id=league.id)

    target = get_object_or_404(User, id=user_id)

    LeagueMembership.objects.filter(user=target, league=league).delete()
    # Removing a member also revokes any co-commissioner role they held.
    league.co_commissioners.remove(target)

    messages.success(request, f"Removed {target.username} from {league.name}.")
    return redirect('manage_league', league_id=league.id)


def join_via_invite(request, code):
    """Branded invite landing page + join action for a shareable invite link.

    GET renders a preview of the league (with Open Graph tags for rich link
    previews when the link is texted/shared). POSTing the "Join League" form
    adds the user; anonymous visitors are routed to signup first, carrying the
    invite along so they land back here after registering.
    """
    league = get_object_or_404(League, join_code=code.upper(), is_approved=True)

    already_member = (
        request.user.is_authenticated
        and league.members.filter(id=request.user.id).exists()
    )
    join_locked = league.is_join_locked()

    # A visitor is trying to join when they submit the Join form (POST) OR when
    # they return here authenticated straight from signup/login. We carry a
    # ?join=1 flag on the "next" URL so registration flows directly into league
    # membership instead of dumping them back on the preview page to click again.
    wants_join = request.method == 'POST' or request.GET.get('join') == '1'

    # Season's underway — existing members can still open the league, but nobody
    # new can join through the invite link.
    if wants_join and join_locked and not already_member:
        messages.error(request, f"{league.name} is locked — the season has already started, so new members can't join.")
        return redirect('join_via_invite', code=league.join_code)

    if wants_join:
        if not request.user.is_authenticated:
            from urllib.parse import urlencode
            return redirect(
                f"{reverse('signup')}?{urlencode({'next': f'{request.path}?join=1'})}"
            )

        if not already_member:
            LeagueMembership.objects.get_or_create(user=request.user, league=league)
            messages.success(request, f"You've joined {league.name}!")
            try:
                if request.user.email:
                    html_message = render_to_string('emails/league_joined.html', {
                        'username': request.user.username,
                        'league_name': league.name,
                        'site_url': settings.SITE_URL,
                    })
                    send_mail(
                        f'Welcome to {league.name}!',
                        f'You have joined "{league.name}". Make picks at: {settings.SITE_URL}/picks/',
                        settings.DEFAULT_FROM_EMAIL,
                        [request.user.email],
                        html_message=html_message,
                        fail_silently=True,
                    )
            except Exception as e:
                print(f"Invite join email failed: {e}")

        return redirect('league_detail', league_id=league.id)

    context = {
        'league': league,
        'already_member': already_member,
        'join_locked': join_locked,
        'member_count': league.members.count(),
        'invite_url': request.build_absolute_uri(),
    }
    return render(request, 'leagues/invite_landing.html', context)


def invite_redirect(request, invite_code):
    """Backward-compat: old UUID invite links redirect to the new short link."""
    league = get_object_or_404(League, invite_code=invite_code, is_approved=True)
    return redirect('join_via_invite', code=league.join_code)