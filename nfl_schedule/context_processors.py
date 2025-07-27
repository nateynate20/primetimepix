# nfl_schedule/context_processors.py

from .models import NFLGame
from django.utils import timezone

def scores_ticker(request):
    today = timezone.now().date()
    ticker_games = NFLGame.objects.filter(date__gte=today).exclude(status='Scheduled').order_by('date')
    return {'scores_ticker': ticker_games}
