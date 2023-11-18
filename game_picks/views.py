#game_picks/views.py
from django.shortcuts import render, redirect
from nfl_schedule.models import NFLGame
from .models import GameSelection
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from game_picks.models import GameSelection
from .forms import GameSelectionForm  # Import the form
from game_picks.models import UserRecord

@login_required(login_url='login')
def display_nfl_schedule(request):
    if request.method == 'POST':
        # Create a form instance and populate it with data from the request:
        form = GameSelectionForm(request.POST)

        if form.is_valid():
            # Get the selected game from the form
            game = form.cleaned_data['game']

            # Check if a prediction already exists for this game
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

    games = NFLGame.objects.all()
    predictions = GameSelection.objects.filter(user=request.user, game__in=games)

    context = {
        'games': games,
        'predictions': predictions,
        'form': form,  # Add the form to the context
    }

    return render(request, 'nfl_schedule/schedule.html', context)

def standings(request):
    user_records = UserRecord.objects.order_by('-correct_predictions')
    return render(request, 'nfl_schedule/standings.html', {'user_records': user_records})