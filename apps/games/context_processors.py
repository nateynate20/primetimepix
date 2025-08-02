from django.utils import timezone
from datetime import time, date
from .models import NFLGame

# Define primetime start cutoff (roughly 8 PM or later ET)
PRIMETIME_START = time(20, 0)  # 8:00 PM

# Define known U.S. holidays relevant to NFL
HOLIDAY_DATES = {
    # These can be dynamically set based on year in production
    "thanksgiving": lambda year: get_thanksgiving_date(year),
    "christmas": lambda year: date(year, 12, 25),
    "new_years": lambda year: date(year + 1, 1, 1),
}

def get_thanksgiving_date(year):
    """Return the date of Thanksgiving (4th Thursday of November)."""
    from datetime import datetime, timedelta
    # Nov 1st
    nov1 = date(year, 11, 1)
    # Find the first Thursday
    first_thursday = nov1 + timedelta(days=(3 - nov1.weekday()) % 7)
    # Thanksgiving is the 4th Thursday
    return first_thursday + timedelta(weeks=3)

def live_scores_ticker(request):
    today = timezone.now().date()
    year = today.year

    # Dynamically generate holiday dates
    holiday_dates = {name: fn(year) for name, fn in HOLIDAY_DATES.items()}
    holiday_dates["new_years"] = HOLIDAY_DATES["new_years"](year - 1 if today.month == 1 else year)

    # Filter for:
    # - Primetime games (start at or after 8 PM)
    # - OR Holiday games (Thanksgiving, Christmas, New Year's)
    games = NFLGame.objects.filter(date__gte=today).exclude(status='Scheduled')
    primetime_or_holiday = games.filter(
        start_time__gte=PRIMETIME_START
    ) | games.filter(
        date__in=holiday_dates.values()
    )

    return {
        'scores_ticker': primetime_or_holiday.order_by('date', 'start_time')[:5]
    }
