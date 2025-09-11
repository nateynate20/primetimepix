# apps/games/context_processors.py
from datetime import date, timedelta, time

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

# No live ticker included
