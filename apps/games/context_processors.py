from django.utils import timezone
from django.db.models import Q
from datetime import time, date, timedelta
from .models import Game

# Define primetime start time (8:00 PM ET)
# apps/games/context_processors.py

PRIMETIME_START = time(20, 0)  # 8:00 PM

def primetime_games(request):
    now = timezone.now()
    season_start = timezone.datetime(now.year, 9, 1, tzinfo=timezone.utc)  # Sept 1 of current year

    games = Game.objects.filter(
        start_time__gte=season_start,
        start_time__time__gte=PRIMETIME_START
    ).order_by('start_time')

    return {'primetime_games': games}







def get_thanksgiving_date(year):
    """Return the date of Thanksgiving (4th Thursday of November)."""
    nov1 = date(year, 11, 1)
    first_thursday = nov1 + timedelta(days=(3 - nov1.weekday()) % 7)
    return first_thursday + timedelta(weeks=3)

# Define holiday lookup functions
HOLIDAY_DATES = {
    "thanksgiving": get_thanksgiving_date,
    "christmas": lambda year: date(year, 12, 25),
    "new_years": lambda year: date(year + 1, 1, 1),
}

def live_scores_ticker(request):
    now = timezone.now()
    today = now.date()
    year = today.year

    # Generate dynamic holiday dates for the current year
    holiday_dates = {name: fn(year) for name, fn in HOLIDAY_DATES.items()}

    # Edge case: If today is in January, New Year's Day might be from the previous season
    if today.month == 1:
        holiday_dates["new_years"] = HOLIDAY_DATES["new_years"](year - 1)

    # Pull games that have already started and are not still marked as "scheduled"
    games = Game.objects.filter(start_time__lte=now).exclude(status__iexact="scheduled")

    # Filter for:
    # - Games that are primetime (8 PM or later)
    # - OR games on holiday dates
    primetime_or_holiday_games = games.filter(
        Q(start_time__time__gte=PRIMETIME_START) |
        Q(start_time__date__in=holiday_dates.values())
    )

    # Return the 5 most recent eligible games for the ticker
    return {
        "scores_ticker": primetime_or_holiday_games.order_by("start_time")[:5]
    }
