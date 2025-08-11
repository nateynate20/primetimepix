# apps/games/context_processors.py

from django.utils import timezone
from datetime import time, date, timedelta
from .models import Game


# Define primetime start cutoff (8:00 PM ET)
PRIMETIME_START = time(20, 0)

# Define known U.S. holidays relevant to NFL
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
    now = timezone.now()
    today = now.date()
    year = today.year

    # Dynamically generate holiday dates
    holiday_dates = {name: fn(year) for name, fn in HOLIDAY_DATES.items()}
    if today.month == 1:
        holiday_dates["new_years"] = HOLIDAY_DATES["new_years"](year - 1)

    # Get all non-scheduled games that have started already
    games = Game.objects.filter(start_time__lte=now).exclude(status="Scheduled")

    # Filter for:
    # - Primetime games (starting 8PM or later)
    # - OR Holiday games
    primetime_or_holiday = games.filter(
        start_time__time__gte=PRIMETIME_START
    ) | games.filter(
        start_time__date__in=holiday_dates.values()
    )

    return {
        "scores_ticker": primetime_or_holiday.order_by("start_time")[:5]
    }
