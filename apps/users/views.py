from django.shortcuts import render, redirect
from django.utils.http import url_has_allowed_host_and_scheme
from django.contrib.auth import login, logout
from django.contrib import messages
from django.contrib.auth.forms import AuthenticationForm, PasswordResetForm
from apps.users.forms import SignupUserForm
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.http import JsonResponse, HttpResponse
import traceback
from django.views.decorators.csrf import csrf_exempt

from apps.games.models import Game
from apps.games.utils import get_current_week_dates, is_primetime_game
from apps.picks.models import Pick
from apps.users.models import Profile  # Assuming Profile model exists


# --------------------------------------
# Email Testing (commented out)
# --------------------------------------
# def test_email(request):
#     """Test email configuration"""
#     try:
#         result = send_mail(
#             'Test Email from PrimeTimePix',
#             'If you receive this, email is working!',
#             settings.DEFAULT_FROM_EMAIL,
#             ['evansna05@gmail.com'],  # Send to yourself
#             fail_silently=False,
#         )
#         return JsonResponse({
#             'success': True,
#             'message': f'Email sent successfully! Result: {result}',
#             'settings': {
#                 'host': settings.EMAIL_HOST,
#                 'port': settings.EMAIL_PORT,
#                 'user': settings.EMAIL_HOST_USER,
#                 'from': settings.DEFAULT_FROM_EMAIL,
#             }
#         })
#     except Exception as e:
#         return JsonResponse({
#             'success': False,
#             'error': str(e),
#             'settings': {
#                 'host': settings.EMAIL_HOST,
#                 'port': settings.EMAIL_PORT,
#                 'user': settings.EMAIL_HOST_USER[:3] + '***',  # Partial for security
#             }
#         })


# --------------------------------------
# User Signup
# --------------------------------------
def _get_safe_next(request):
    """Return a validated ?next= redirect target, or None if unsafe/absent."""
    next_url = request.POST.get('next') or request.GET.get('next')
    if next_url and url_has_allowed_host_and_scheme(
        next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return next_url
    return None


def signup(request):
    if request.method == "POST":
        form = SignupUserForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Welcome to PrimeTimePix! Check your email for next steps.")

            # Send welcome email
            try:
                html_message = render_to_string('emails/welcome.html', {
                    'username': user.username,
                    'site_url': settings.SITE_URL,
                })
                send_mail(
                    'Welcome to PrimeTimePix!',
                    f'Hi {user.username}, welcome to PrimeTimePix! Make your primetime picks at {settings.SITE_URL}/picks/',
                    settings.DEFAULT_FROM_EMAIL,
                    [user.email],
                    html_message=html_message,
                    fail_silently=True,
                )
            except Exception as e:
                print(f"Email sending failed: {e}")

            return redirect(_get_safe_next(request) or 'dashboard')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = SignupUserForm()
    return render(request, 'registration/signup.html', {
        'form': form,
        'next': _get_safe_next(request) or '',
    })


# --------------------------------------
# Debug Password Reset
# --------------------------------------
def debug_password_reset(request):
    """Debug password reset with detailed error logging"""
    debug_info = {
        'method': request.method,
        'errors': [],
        'info': [],
        'success': False
    }
    
    try:
        debug_info['settings'] = {
            'EMAIL_HOST': settings.EMAIL_HOST,
            'EMAIL_HOST_USER': settings.EMAIL_HOST_USER[:5] + '***' if settings.EMAIL_HOST_USER else 'NOT SET',
            'EMAIL_HOST_PASSWORD': 'SET' if settings.EMAIL_HOST_PASSWORD else 'NOT SET',
        }
        
        if request.method == 'POST':
            email = request.POST.get('email', '')
            debug_info['info'].append(f"Testing with email: {email}")
            
            try:
                form = PasswordResetForm({'email': email})
                if form.is_valid():
                    form.save(request=request)
                    debug_info['success'] = True
                    debug_info['info'].append("Password reset email sent!")
                else:
                    debug_info['errors'].append(f"Form errors: {form.errors}")
            except Exception as e:
                debug_info['errors'].append(f"Error: {str(e)}")
                debug_info['errors'].append(f"Traceback: {traceback.format_exc()}")
                
            return JsonResponse(debug_info, json_dumps_params={'indent': 2})
        
        else:
            html = f"""
            <html><body style="font-family: Arial; margin: 40px;">
            <h2>Debug Password Reset</h2>
            <p>Settings: EMAIL_HOST_USER = {debug_info['settings']['EMAIL_HOST_USER']}</p>
            <form method="post">
                <input type="hidden" name="csrfmiddlewaretoken" value="{request.META.get('CSRF_COOKIE', '')}">
                <input type="email" name="email" placeholder="Enter email" required>
                <button type="submit">Test Reset</button>
            </form>
            </body></html>
            """
            return HttpResponse(html)
            
    except Exception as e:
        debug_info['errors'].append(f"Critical error: {str(e)}")
        debug_info['errors'].append(f"Traceback: {traceback.format_exc()}")
        return JsonResponse(debug_info, json_dumps_params={'indent': 2})


# --------------------------------------
# Dashboard
# --------------------------------------
@login_required
def dashboard(request):
    user = request.user

    from django.utils import timezone
    from apps.games.utils import get_current_nfl_week
    from apps.leagues.models import League

    current_week = get_current_nfl_week()

    # Leagues (alphabetical, matching the picks page default).
    user_leagues = League.objects.filter(members=user, is_approved=True).order_by("name")

    # Which league the dashboard is focused on. Members of multiple leagues can
    # switch via ?league=<id>; otherwise we default to the first alphabetically
    # (same default as the picks page). Invalid/unauthorized ids fall back.
    requested_id = request.GET.get("league")
    primary_league = None
    if requested_id:
        primary_league = user_leagues.filter(id=requested_id).first()
    if primary_league is None:
        primary_league = user_leagues.first()

    week_games = Game.objects.filter(
        game_type='regular',
        week=current_week,
    ).order_by("start_time")

    primetime_games = [g for g in week_games if g.is_primetime]

    # Show pick status for the user's primary league so it lines up with the
    # picks page (which now defaults to that same league).
    user_picks_qs = Pick.objects.filter(user=user, game__in=primetime_games)
    if primary_league:
        user_picks_qs = user_picks_qs.filter(league=primary_league)
    picks_dict = {p.game_id: p for p in user_picks_qs.select_related("game")}

    now = timezone.now()
    next_game = None
    picked_count = 0
    open_unpicked = 0
    for game in primetime_games:
        game.user_pick = picks_dict.get(game.id)
        game.has_score = game.status in ['final', 'in_progress'] and (game.home_score is not None or game.away_score is not None)
        game.away_is_winner = game.winner == game.away_team if game.winner else False
        game.home_is_winner = game.winner == game.home_team if game.winner else False
        game.is_open = game.status == 'scheduled' and game.start_time > now
        if game.user_pick:
            picked_count += 1
        elif game.is_open:
            open_unpicked += 1
        if game.is_open and (next_game is None or game.start_time < next_game.start_time):
            next_game = game

    # Personal standing snapshot in the primary league.
    my_rank = None
    my_record = None
    my_points = None
    my_accuracy = None
    total_in_league = 0
    standings_snapshot = []
    if primary_league:
        standings = primary_league.get_standings()
        total_in_league = len(standings)
        for idx, row in enumerate(standings, start=1):
            row['rank'] = idx
            if row['user'] == user:
                my_rank = idx
                my_record = row['record']
                my_points = row['total_points']
                my_accuracy = row['accuracy']
        standings_snapshot = standings[:5]

    # Cross-league glance for members of more than one league: their rank and
    # record in each, so they don't have to open every league one by one.
    league_summaries = []
    if user_leagues.count() > 1:
        for lg in user_leagues:
            rank = record = points = None
            lg_standings = lg.get_standings()
            for idx, row in enumerate(lg_standings, start=1):
                if row['user'] == user:
                    rank, record, points = idx, row['record'], row['total_points']
                    break
            league_summaries.append({
                'league': lg,
                'rank': rank,
                'record': record,
                'points': points,
                'total': len(lg_standings),
                'is_active': primary_league and lg.id == primary_league.id,
            })

    # Streaks & badges — computed from the user's global pick history. Stats
    # aren't refreshed by the grading pipeline, so recompute on load to keep the
    # streak/badges honest. `current_streak` can be negative (a losing skid).
    from apps.picks.models import UserStats
    from apps.picks.badges import compute_badges
    stats = UserStats.get_or_create_for_user(user)
    stats.update_stats()
    stats.current_streak_abs = abs(stats.current_streak)
    badges = compute_badges(stats)
    earned_badge_count = sum(1 for b in badges if b['earned'])

    # Get unread notifications
    from apps.users.models import Notification
    notifications = Notification.objects.filter(user=user, is_read=False)[:5]

    context = {
        'user': user,
        'stats': stats,
        'badges': badges,
        'earned_badge_count': earned_badge_count,
        'league': primary_league,  # backwards-compatible alias
        'user_leagues': user_leagues,
        'primary_league': primary_league,
        'league_summaries': league_summaries,
        'primetime_games': primetime_games,
        'current_week': current_week,
        'picked_count': picked_count,
        'open_unpicked': open_unpicked,
        'total_primetime': len(primetime_games),
        'next_game': next_game,
        'my_rank': my_rank,
        'my_record': my_record,
        'my_points': my_points,
        'my_accuracy': my_accuracy,
        'total_in_league': total_in_league,
        'standings_snapshot': standings_snapshot,
        'notifications': notifications,
    }
    return render(request, 'user_dashboard.html', context)


# --------------------------------------
# Landing & Login
# --------------------------------------
def landing_page(request):
    return render(request, 'nflpix/landing.html')


def login_user(request):
    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f"Welcome back, {user.username}!")
            return redirect(_get_safe_next(request) or 'dashboard')
        else:
            messages.error(request, "Invalid username or password.")
    else:
        form = AuthenticationForm()
    return render(request, 'registration/login.html', {
        'form': form,
        'next': _get_safe_next(request) or '',
    })


# --------------------------------------
# Logout
# --------------------------------------
@require_POST
def logout_user(request):
    logout(request)
    messages.success(request, "You have successfully logged out.")
    return redirect('landing_page')


# --------------------------------------
# Send Password Reset Emails to First-Time Users (once)
# --------------------------------------
@csrf_exempt
def send_pending_password_resets(request):
    """
    Sends password reset emails to users who haven't logged in yet.
    Marks each user as 'reset_sent' in Profile to avoid resending.
    """
    if request.method not in ['GET', 'POST']:
        return HttpResponse("Only GET/POST allowed.", status=405)

    from django.contrib.auth.models import User

    users = User.objects.filter(is_active=True, last_login__isnull=True)
    sent_emails, failed_emails = [], []

    for user in users:
        try:
            profile, _ = Profile.objects.get_or_create(user=user)

            # Skip if already sent (only if the field exists)
            if hasattr(profile, "password_reset_sent") and profile.password_reset_sent:
                print(f"[SKIP] Already sent to {user.email}")
                continue

            if not user.email:
                failed_emails.append({'email': None, 'reason': 'No email'})
                print(f"[FAIL] User {user.username} has no email")
                continue

            form = PasswordResetForm({'email': user.email})
            if form.is_valid():
                form.save(
                    request=request,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    email_template_name='registration/password_reset_email.html',
                    subject_template_name='registration/password_reset_subject.txt',
                )
                # Mark as sent (if field exists)
                if hasattr(profile, "password_reset_sent"):
                    profile.password_reset_sent = True
                    profile.save()

                sent_emails.append(user.email)
                print(f"[EMAIL SENT] Reset email sent to: {user.email}")
            else:
                failed_emails.append({'email': user.email, 'error': form.errors})
                print(f"[FAIL] Form invalid for {user.email}: {form.errors}")
        except Exception as e:
            failed_emails.append({'email': user.email, 'error': str(e)})
            print(f"[ERROR] Failed for {user.email}: {e}")

    summary = {
        'total_users': users.count(),
        'total_sent': len(sent_emails),
        'total_failed': len(failed_emails),
        'sent_emails': sent_emails,
        'failed_emails': failed_emails,
    }

    print(f"=== SUMMARY === {summary}")  # 👈 visible in Render logs

    return JsonResponse(summary, json_dumps_params={'indent': 2})


@login_required
def dismiss_notifications(request):
    """Mark all notifications as read for the current user."""
    from apps.users.models import Notification
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    messages.info(request, "All notifications dismissed.")
    return redirect('dashboard')


@login_required
def toggle_reminders(request):
    """Toggle email reminders on/off."""
    profile = request.user.profile
    profile.email_reminders_enabled = not profile.email_reminders_enabled
    profile.save()
    status = "enabled" if profile.email_reminders_enabled else "disabled"
    messages.success(request, f"Email reminders {status}.")
    return redirect('dashboard')


@login_required
def edit_profile(request):
    """Allow users to edit their team name, email, and preferences."""
    from apps.users.forms import ProfileEditForm

    profile = request.user.profile

    if request.method == 'POST':
        form = ProfileEditForm(request.POST, user=request.user)
        if form.is_valid():
            profile.team_name = form.cleaned_data['team_name']
            profile.email_reminders_enabled = form.cleaned_data['email_reminders_enabled']
            profile.save()

            request.user.email = form.cleaned_data['email']
            request.user.save()

            messages.success(request, "Profile updated successfully.")
            return redirect('dashboard')
    else:
        form = ProfileEditForm(user=request.user, initial={
            'team_name': profile.team_name,
            'email': request.user.email,
            'email_reminders_enabled': profile.email_reminders_enabled,
        })

    return render(request, 'registration/edit_profile.html', {'form': form})