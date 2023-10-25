# nflpix/views.py
from django.shortcuts import render
from nfl_schedule.models import NFLGame


def display_nfl_schedule(request):
    games = NFLGame.objects.all()  # Query all NFL games

    return render(request, 'nflpix/schedule.html', {'games': games})

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