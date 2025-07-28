from django.utils import timezone
from .models import NFLGame

def live_scores_ticker(request):
    today = timezone.now().date()
    games = NFLGame.objects.filter(date__gte=today).exclude(status='Scheduled').order_by('date', 'start_time')[:5]
    return {'scores_ticker': games}
