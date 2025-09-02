from datetime import date, timedelta, time, datetime
import pytz
from django.utils import timezone

# Primetime definition (Eastern Time)
PRIMETIME_START = time(20, 0)  # 8:00 PM ET
PRIMETIME_END = time(23, 59, 59)  # end of evening window

EASTERN = pytz.timezone('US/Eastern')

def to_eastern(dt):
    if dt.tzinfo is None:
        # assume UTC if naive
        dt = pytz.utc.localize(dt)
    return dt.astimezone(EASTERN)

def is_datetime_primetime(dt):
    """Return True if the given datetime falls within primetime windows.
    - Conservative rule: start time between 8:00 PM and 11:59 PM ET.
    - Allows special-case days (Thursday, Sunday, Monday) which are typical primetime nights.
    """
    if dt is None:
        return False
    try:
        et = to_eastern(dt)
        t = et.time()
        weekday = et.weekday()  # Mon=0 ... Sun=6
        # Common primetime nights: Sunday Night Football, Monday Night, Thursday Night
        if weekday in (0, 3, 6):  # Monday(0), Thursday(3), Sunday(6)
            return PRIMETIME_START <= t <= PRIMETIME_END
        # Also allow any game starting >= PRIMETIME_START regardless of weekday (conservative)
        return PRIMETIME_START <= t <= PRIMETIME_END
    except Exception:
        return False

def get_week_date_range(year, week):
    """Return (start_date, end_date) for the NFL week using a simple approximation.
    This helper is intentionally small — schedule ingestion should rely on nfl_data_py.
    """
    # Find first Thursday of the year to approximate week boundaries (simple heuristic)
    jan1 = date(year, 1, 1)
    start = jan1 + timedelta(days=(3 - jan1.weekday()) % 7)  # first Thursday
    week_start = start + timedelta(weeks=week-1)
    week_end = week_start + timedelta(days=6)
    return week_start, week_end
