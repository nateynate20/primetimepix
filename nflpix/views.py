# nflpix/views.py
from django.shortcuts import redirect, render
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from nfl_schedule.models import NFLGame
from .models import GameSelection


@login_required
def display_nfl_schedule(request):
    # Handle both the scenario when a user logs in and when they sign up
    if request.method == 'POST':
        game = request.POST.get('game')
        predicted_winner = request.POST.get('predicted_winner')
        game = NFLGame.objects.get(id=game)

        existing_prediction = GameSelection.objects.filter(user=request.user, game=game).first()
        if existing_prediction:
            existing_prediction.predicted_winner = predicted_winner
            existing_prediction.save()
        else:
            prediction = GameSelection(user=request.user, game=game, predicted_winner=predicted_winner)
            prediction.save()

        # Redirect to the same page to avoid resubmission
        return redirect('nfl_schedule/display_nfl_schedule')

    games = NFLGame.objects.all()  # Query all NFL games
    predictions = GameSelection.objects.filter(user=request.user, game__in=games)
    context = {
        'games': games,
        'predictions': predictions,
    }

    return render(request, 'schedule.html', context)



def landing_page(request):
    return render(request, 'nflpix/landing_page.html', {})
