from datetime import datetime, time, timedelta
from django.utils import timezone
import pytz

# Define primetime start time (8:00 PM)
PRIMETIME_START = time(20, 0)


def get_current_nfl_week():
    """
    Calculate the current NFL week number based on actual NFL schedule.
    NFL season typically starts first Thursday after Labor Day.
    """
    try:
        now = timezone.now()
        current_date = now.date()
        year = current_date.year
        
        # NFL season typically starts in early September
        # For simplicity, we'll use September 5th as approximate season start
        # You can adjust this based on actual NFL calendar
        season_start = datetime(year, 9, 5).date()
        
        # If we're before the season starts, check previous year
        if current_date < season_start:
            season_start = datetime(year - 1, 9, 5).date()
        
        # Calculate weeks since season start
        days_since_start = (current_date - season_start).days
        week_number = (days_since_start // 7) + 1
        
        # NFL regular season is typically 18 weeks
        if week_number > 18:
            return 18  # Playoffs
        
        return max(1, week_number)
    
    except Exception:
        # Fallback to week 1 if calculation fails
        return 1


def get_nfl_week_dates(week_number=None):
    """
    Get the start and end dates for a specific NFL week.
    NFL weeks typically run Thursday to Wednesday.
    """
    if week_number is None:
        week_number = get_current_nfl_week()
    
    try:
        now = timezone.now()
        year = now.year
        
        # Approximate season start (first Thursday in September)
        season_start = datetime(year, 9, 5).date()
        
        # If we're before the season starts, use previous year
        if now.date() < season_start:
            season_start = datetime(year - 1, 9, 5).date()
        
        # Calculate the start of the specified week
        # NFL weeks start on Thursday
        week_start = season_start + timedelta(weeks=week_number - 1)
        
        # Adjust to Thursday if season_start isn't a Thursday
        days_to_thursday = (3 - week_start.weekday()) % 7
        week_start = week_start + timedelta(days=days_to_thursday)
        
        # NFL week ends on Wednesday (6 days later)
        week_end = week_start + timedelta(days=6)
        
        return week_start, week_end
    
    except Exception:
        # Fallback to current calendar week
        today = timezone.now().date()
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)
        return week_start, week_end


def get_current_week_dates():
    """
    Get the current NFL week dates (Thursday to Wednesday).
    This replaces the old calendar week function.
    """
    return get_nfl_week_dates()


def filter_primetime_games(games_queryset):
    """
    Filter games queryset to only include primetime games.
    Enhanced to handle edge cases better.
    """
    try:
        eastern = pytz.timezone('US/Eastern')
        primetime_games = []
        
        for game in games_queryset:
            try:
                # Check if game has is_primetime property first
                if hasattr(game, 'is_primetime') and game.is_primetime:
                    primetime_games.append(game)
                else:
                    # Fallback: check time manually
                    if game.start_time:
                        et_time = game.start_time.astimezone(eastern)
                        if et_time.time() >= PRIMETIME_START:
                            primetime_games.append(game)
            except (AttributeError, TypeError):
                # Skip games that don't have proper start_time
                continue
        
        return primetime_games
    
    except Exception:
        # If filtering fails, return empty list
        return []


def is_primetime_game(game):
    """
    Check if a single game is a primetime game.
    Enhanced with better logic.
    """
    try:
        # Check if game has is_primetime property first
        if hasattr(game, 'is_primetime'):
            return game.is_primetime
        
        # Fallback: check time manually
        if not game.start_time:
            return False
            
        eastern = pytz.timezone('US/Eastern')
        et_time = game.start_time.astimezone(eastern)
        
        # Check for primetime slots:
        # Monday Night Football (8:20 PM ET)
        # Thursday Night Football (8:20 PM ET) 
        # Sunday Night Football (8:20 PM ET)
        # Holiday games (any time)
        
        weekday = et_time.weekday()  # 0=Monday, 3=Thursday, 6=Sunday
        game_time = et_time.time()
        
        # Monday, Thursday, Sunday night games
        if weekday in [0, 3, 6] and game_time >= PRIMETIME_START:
            return True
            
        # Holiday games (check specific dates)
        if is_holiday_game(et_time.date()):
            return True
            
        return False
    
    except (AttributeError, TypeError):
        return False


def is_holiday_game(game_date):
    """Check if a game is on a holiday."""
    year = game_date.year
    
    # Thanksgiving (4th Thursday of November)
    thanksgiving = get_thanksgiving_date(year)
    if game_date == thanksgiving:
        return True
        
    # Christmas games
    if game_date.month == 12 and game_date.day in [24, 25]:
        return True
        
    # New Year's Day games
    if game_date.month == 1 and game_date.day == 1:
        return True
        
    return False


def get_thanksgiving_date(year):
    """Return the date of Thanksgiving (4th Thursday of November)."""
    from datetime import date
    nov1 = date(year, 11, 1)
    first_thursday = nov1 + timedelta(days=(3 - nov1.weekday()) % 7)
    return first_thursday + timedelta(weeks=3)


def debug_primetime_games():
    """
    Debug function to check what games are being considered primetime.
    You can call this in Django shell to troubleshoot.
    """
    from apps.games.models import Game
    
    week_start, week_end = get_current_week_dates()
    games = Game.objects.filter(
        start_time__date__gte=week_start,
        start_time__date__lte=week_end,
    )
    
    print(f"NFL Week dates: {week_start} to {week_end}")
    print(f"Total games found: {games.count()}")
    
    for game in games:
        is_pt = is_primetime_game(game)
        et_time = game.display_time_et
        print(f"{game.away_team} @ {game.home_team}")
        print(f"  Start time: {et_time}")
        print(f"  Primetime: {is_pt}")
        print(f"  Model says primetime: {game.is_primetime}")
        print("---")
    
    primetime_games = [g for g in games if is_primetime_game(g)]
    print(f"Primetime games found: {len(primetime_games)}")
    
    return games, primetime_games