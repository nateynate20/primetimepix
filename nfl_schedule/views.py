from django.shortcuts import render
from django.utils import timezone
from django.core.paginator import Paginator
from django.db.models import Q
from nfl_schedule.models import NFLGame
from dashboard.views import fetch_recent_scores  # Adjust if needed

# 1. Import data from TheSportsDB API
def import_nfl_schedule(request):
    try:
        scores = fetch_recent_scores(4391)  # NFL league ID
    except Exception as e:
        return render(request, 'nflpix/error_page.html', {'error_message': str(e)})

    if scores:
        NFLGame.objects.all().delete()

        for game in scores:
            NFLGame.objects.create(
                week=None,
                date=game.get("date"),
                home_team=game.get("home_team"),
                away_team=game.get("away_team"),
                start_time=None,
                home_score=game.get("home_score") or 0,
                away_score=game.get("away_score") or 0,
                status=game.get("status") or "Final",
                home_logo=game.get("home_logo") or "",
                away_logo=game.get("away_logo") or "",
            )

        return render(request, 'nflpix/success_page.html', {'message': 'Live NFL scores imported successfully'})
    else:
        return render(request, 'nflpix/error_page.html', {'error_message': 'No data returned from the API.'})

# 2. HTMX refresh (if used in ticker)
def htmx_refresh_scores(request):
    today = timezone.now().date()
    ticker_games = NFLGame.objects.filter(date__gte=today).exclude(status="Scheduled").order_by("date")
    return render(request, 'nfl_schedule/partials/_scores.html', {'scores_ticker': ticker_games})

# 3. Full scores view with filter and pagination
def view_scores_page(request):
    today = timezone.now().date()
    team_query = request.GET.get('team', '')
    page_number = request.GET.get('page', 1)

    base_query = NFLGame.objects.filter(date__gte=today).order_by('date')
    if team_query:
        base_query = base_query.filter(Q(home_team__icontains=team_query) | Q(away_team__icontains=team_query))

    paginator = Paginator(base_query, 5)
    page_obj = paginator.get_page(page_number)

    all_teams = NFLGame.objects.values_list('home_team', flat=True).distinct()

    return render(request, 'views_score.html', {
        'games': page_obj,
        'team_query': team_query,
        'teams': sorted(set(all_teams)),
    })
