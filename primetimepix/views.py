from django.shortcuts import render
from apps.games.models import Game
from django.contrib.auth.models import User

def landing_page(request):
    context = {
        'total_games': Game.objects.count(),
        'primetime_games': sum(1 for g in Game.objects.all() if g.is_primetime),
        'active_users': User.objects.filter(is_active=True).count(),
    }
    return render(request, 'nflpix/landing_page.html', context)