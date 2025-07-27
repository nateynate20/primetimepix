import requests
from django.conf import settings
from django.shortcuts import render
from django.utils import timezone
from django.core.paginator import Paginator
from django.db.models import Q
from nfl_schedule.models import NFLGame


def fetch_recent_scores(league_id):
    url = f"https://www.thesportsdb.com/api/v1/json/{settings.THESPORTSDB_API_KEY}/eventspastleague.php?id={league_id}"
    try:
        res = requests.get(url)
        data = res.json()
        events = data.get('events', [])[:5]

        scores = []
        for event in events:
            scores.append({
                "match": event.get("strEvent"),
                "home_team": event.get("strHomeTeam"),
                "away_team": event.get("strAwayTeam"),
                "home_score": event.get("intHomeScore") or 0,
                "away_score": event.get("intAwayScore") or 0,
                "date": event.get("dateEvent"),
                "status": event.get("strStatus") or "Final",
                "home_logo": event.get("strHomeTeamBadge") or "",
                "away_logo": event.get("strAwayTeamBadge") or "",
            })

        return scores
    except Exception as e:
        print(f"Error fetching scores for league {league_id}: {e}")
        return []


def import_nfl_schedule(request):
    try:
        scores = fetch_recent_scores(4391)  # NFL league ID
    except Exception as e:
        return render(request, 'nflpix/error_page.html', {'error_message': str(e)})

    if scores:
        # Clear existing games before importing new ones
        NFLGame.objects.all().delete()

        # Save each game fetched from API to DB
        for game in scores:
            NFLGame.objects.create(
                week=None,
                date=game.get("date"),
                home_team=game.get("home_team"),
                away_team=game.get("away_team"),
                start_time=None,
                home_score=game.get("home_score"),
                away_score=game.get("away_score"),
                status=game.get("status"),
                home_logo=game.get("home_logo"),
                away_logo=game.get("away_logo"),
            )

        return render(request, 'nflpix/success_page.html', {'message': 'Live NFL scores imported successfully'})
    else:
        return render(request, 'nflpix/error_page.html', {'error_message': 'No data returned from the API.'})


def htmx_refresh_scores(request):
    today = timezone.now().date()
    ticker_games = NFLGame.objects.filter(date__gte=today).exclude(status="Scheduled").order_by("date")
    return render(request, 'nfl_schedule/partials/_scores.html', {'scores_ticker': ticker_games})


def view_scores_page(request):
    today = timezone.now().date()
    team_query = request.GET.get('team', '')
    page_number = request.GET.get('page', 1)

    # Filter upcoming games, filter by team if requested
    base_query = NFLGame.objects.filter(date__gte=today).order_by('date')
    if team_query:
        base_query = base_query.filter(Q(home_team__icontains=team_query) | Q(away_team__icontains=team_query))

    paginator = Paginator(base_query, 5)
    page_obj = paginator.get_page(page_number)

    # Get distinct team names for filter dropdown
    all_teams = NFLGame.objects.values_list('home_team', flat=True).distinct()

    return render(request, 'views_score.html', {
        'games': page_obj,
        'team_query': team_query,
        'teams': sorted(set(all_teams)),
    })
