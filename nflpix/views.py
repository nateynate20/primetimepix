# nflpix/views.py
from django.shortcuts import redirect, render
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, authenticate
from django.contrib.auth.forms import AuthenticationForm
from nfl_schedule.models import NFLGame
from .models import GameSelection
from django.contrib.auth.views import LoginView
from .forms import CustomUserCreationForm

class CustomLoginView(LoginView):
    template_name = 'nflpix/registration/login.html'
@login_required
def display_nfl_schedule(request):
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
        return redirect('display_nfl_schedule')

    games = NFLGame.objects.all()  # Query all NFL games
    predictions = GameSelection.objects.filter(user=request.user, game__in=games)
    context = {
        'games': games,
        'predictions': predictions,
    }

    return render(request, 'nflpix/schedule.html', context)

def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(data=request.POST)

        if form.is_valid():
            email = form.cleaned_data['username']  # Assuming the email field is used for authentication
            password = form.cleaned_data['password']
            user = authenticate(request, username=email, password=password)

            if user is not None:
                login(request, user)  # Log the user in after successful authentication
                return redirect('display_nfl_schedule')  # Redirect to the desired page

    else:
        form = AuthenticationForm()

    return render(request, 'nflpix/registration/login.html', {'form': form})


def landing_page(request):
    # You can customize this view to include any content you want to display on the landing page.
    # For example, you can provide a welcome message, introduction, or links to other sections of your app.

    # Example content:
    welcome_message = "Welcome to NFL Pick App"
    introduction = "Get ready to pick your favorite NFL teams and follow their schedules."
    learn_more_link = "/nfl_schedule/"  # You can provide a link to your NFL schedule page

    return render(request, 'nflpix/landing_page.html', {
        'welcome_message': welcome_message,
        'introduction': introduction,
        'learn_more_link': learn_more_link,
    })
