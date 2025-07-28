from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from nfl_schedule.models import NFLGame

@login_required(login_url='login')
def view_schedule_page(request):
    selected_team = request.GET.get('team', '').strip()
    games = NFLGame.objects.all().order_by('date', 'start_time')

    if selected_team:
        games = games.filter(
            Q(home_team__icontains=selected_team) | Q(away_team__icontains=selected_team)
        )

    teams = NFLGame.objects.values_list('home_team', flat=True).distinct().order_by('home_team')

    paginator = Paginator(games, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'games': page_obj,
        'teams': teams,
        'selected_team': selected_team,
    }
    return render(request, 'schedule.html', context)
