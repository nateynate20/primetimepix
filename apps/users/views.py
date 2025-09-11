from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib import messages
from django.contrib.auth.forms import AuthenticationForm
from apps.users.forms import SignupUserForm
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.conf import settings

from apps.games.models import Game
from apps.games.utils import get_current_week_dates, is_primetime_game
from apps.picks.models import Pick

def signup(request):
    if request.method == "POST":
        form = SignupUserForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            
            # Send welcome email
            try:
                send_mail(
                    'Welcome to PrimeTimePix!',
                    f'Hi {user.username},\n\nWelcome to PrimeTimePix! You can now make picks for NFL primetime games.\n\nGet started: https://primetimepix.onrender.com/picks/\n\nGood luck!\nThe PrimeTimePix Team',
                    settings.DEFAULT_FROM_EMAIL,
                    [user.email],
                    fail_silently=True,
                )
            except Exception as e:
                print(f"Email sending failed: {e}")
            
            messages.success(request, "Welcome to PrimeTimePix! Check your email for next steps.")
            return redirect('dashboard')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = SignupUserForm()
    return render(request, 'registration/signup.html', {'form': form})


@login_required
def dashboard(request):
    user = request.user
    leagues = user.leagues.all()
    league = leagues.first() if leagues.exists() else None

    # --- Get current week primetime games ---
    current_week_start, current_week_end = get_current_week_dates()
    primetime_games = Game.objects.filter(
        start_time__date__gte=current_week_start,
        start_time__date__lte=current_week_end,
    ).order_by("week", "start_time")

    primetime_games = [g for g in primetime_games if is_primetime_game(g)]

    # --- Get user's picks for these games ---
    user_picks_qs = Pick.objects.filter(user=user, game__in=primetime_games).select_related("game")
    picks_dict = {p.game.id: p for p in user_picks_qs}

    # Attach pick object to each game - locked status is handled by the Game model's property
    for game in primetime_games:
        game.user_pick = picks_dict.get(game.id)
        # NOTE: game.locked is now a property - no need to set it manually

    context = {
        'user': user,
        'league': league,
        'primetime_games': primetime_games,
    }
    return render(request, 'user_dashboard.html', context)


def landing_page(request):
    return render(request, 'nflpix/landing.html')


def login_user(request):
    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f"Welcome back, {user.username}!")
            return redirect('dashboard')
        else:
            messages.error(request, "Invalid username or password.")
    else:
        form = AuthenticationForm()
    return render(request, 'registration/login.html', {'form': form})


def signup(request):
    if request.method == "POST":
        form = SignupUserForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Account created successfully.")
            return redirect('dashboard')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = SignupUserForm()
    return render(request, 'registration/signup.html', {'form': form})


@require_POST
def logout_user(request):
    logout(request)
    messages.success(request, "You have successfully logged out.")
    return redirect('landing_page')