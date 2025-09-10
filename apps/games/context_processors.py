# apps/games/context_processors.py
from django.utils import timezone
from datetime import time, date, timedelta
from django.core.cache import cache
from .models import Game

# Define primetime start cutoff (8:00 PM ET)
PRIMETIME_START = time(20, 0)

def get_thanksgiving_date(year):
    """Return the date of Thanksgiving (4th Thursday of November)."""
    nov1 = date(year, 11, 1)
    first_thursday = nov1 + timedelta(days=(3 - nov1.weekday()) % 7)
    return first_thursday + timedelta(weeks=3)

HOLIDAY_DATES = {
    "thanksgiving": get_thanksgiving_date,
    "christmas": lambda year: date(year, 12, 25),
    "new_years": lambda year: date(year + 1, 1, 1),
}

def live_scores_ticker(request):
    """
    Industry standard context processor for live scores ticker.
    Includes caching for performance and proper status handling.
    """
    # Use cache to avoid hitting database on every request
    cache_key = "live_scores_ticker_data"
    cached_data = cache.get(cache_key)
    
    if cached_data is not None:
        return {"live_scores_ticker": cached_data}
    
    try:
        now = timezone.now()
        today = now.date()
        year = today.year
        
        # Dynamically generate holiday dates
        holiday_dates = {name: fn(year) for name, fn in HOLIDAY_DATES.items()}
        if today.month == 1:
            holiday_dates["new_years"] = HOLIDAY_DATES["new_years"](year - 1)
        
        # Get games that are currently in progress, recently finished, or starting soon
        time_window_start = now - timedelta(hours=4)  # Include recently finished games
        time_window_end = now + timedelta(hours=1)    # Include games starting soon
        
        games = Game.objects.filter(
            start_time__gte=time_window_start,
            start_time__lte=time_window_end
        ).exclude(status="Scheduled")
        
        # Priority order for ticker display:
        # 1. Live/In Progress games
        # 2. Primetime games (8PM+ or holidays)
        # 3. Recently finished games
        # 4. Games starting soon
        
        live_games = games.filter(status__in=["In Progress", "Live", "Halftime"])
        
        primetime_or_holiday = games.filter(
            start_time__time__gte=PRIMETIME_START
        ) | games.filter(
            start_time__date__in=holiday_dates.values()
        )
        
        # Combine and prioritize
        if live_games.exists():
            # Prioritize live games, then add primetime/holiday games
            ticker_games = list(live_games[:3])  # Max 3 live games
            remaining_slots = 5 - len(ticker_games)
            if remaining_slots > 0:
                additional_games = primetime_or_holiday.exclude(
                    id__in=[game.id for game in ticker_games]
                )[:remaining_slots]
                ticker_games.extend(additional_games)
        else:
            # No live games, show primetime/holiday games
            ticker_games = primetime_or_holiday.order_by("-start_time")[:5]
        
        # Add some recently finished games if we have slots
        if len(ticker_games) < 5:
            recent_finals = games.filter(
                status="Final",
                start_time__gte=now - timedelta(hours=2)
            ).exclude(
                id__in=[game.id for game in ticker_games]
            )[:5 - len(ticker_games)]
            ticker_games.extend(recent_finals)
        
        # Cache for 30 seconds to balance performance and freshness
        cache.set(cache_key, ticker_games, 30)
        
        return {
            "live_scores_ticker": ticker_games
        }
        
    except Exception as e:
        # Log error and return empty list
        print(f"[live_scores_ticker] Error fetching games: {e}")
        return {
            "live_scores_ticker": []
        }