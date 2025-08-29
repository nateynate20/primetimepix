# apps/games/utils.py
from datetime import date, timedelta, time
from django.utils import timezone
import pytz

# Define primetime start time (8:00 PM ET)
PRIMETIME_START = time(20, 0)

def get_thanksgiving_date(year):
    """Return the date of Thanksgiving (4th Thursday of November)."""
    nov1 = date(year, 11, 1)
    first_thursday = nov1 + timedelta(days=(3 - nov1.weekday()) % 7)
    return first_thursday + timedelta(weeks=3)

def get_holiday_dates(year):
    """Get dictionary of holiday dates for NFL special games"""
    return {
        "thanksgiving": get_thanksgiving_date(year),
        "christmas": date(year, 12, 25),
        "new_years": date(year + 1, 1, 1),
    }

def is_primetime_game(game_start_time):
    """Check if a game is considered primetime (8 PM ET or later)"""
    if not game_start_time:
        return False
        
    eastern = pytz.timezone('US/Eastern')
    et_time = game_start_time.astimezone(eastern)
    return et_time.time() >= PRIMETIME_START

def get_current_nfl_week():
    """Get the current NFL week based on the date"""
    now = timezone.now()
    # NFL season typically starts first Thursday of September
    # This is a simplified version - you might want more sophisticated logic
    
    season_start = timezone.datetime(now.year, 9, 1, tzinfo=timezone.utc)
    if now < season_start:
        # If before September, use previous year's season
        season_start = timezone.datetime(now.year - 1, 9, 1, tzinfo=timezone.utc)
    
    # Calculate weeks since season start
    days_since_start = (now - season_start).days
    week_number = (days_since_start // 7) + 1
    
    return min(max(week_number, 1), 18)  # NFL has 18 weeks

def get_week_date_range(year=None, week=None):
    """Get the start and end date for a given NFL week"""
    if not year:
        year = timezone.now().year
    
    if not week:
        week = get_current_nfl_week()
    
    # Start with first Thursday of September (approximate season start)
    season_start = date(year, 9, 1)
    first_thursday = season_start + timedelta(days=(3 - season_start.weekday()) % 7)
    
    week_start = first_thursday + timedelta(weeks=week-1)
    week_end = week_start + timedelta(days=6)
    
    return week_start, week_end

def filter_primetime_games(games):
    """Filter a queryset or list of games to only include primetime games"""
    primetime_games = []
    for game in games:
        if hasattr(game, 'is_primetime') and game.is_primetime:
            primetime_games.append(game)
        elif is_primetime_game(game.start_time):
            primetime_games.append(game)
    
    return primetime_games

def get_team_logos():
    """Return a dictionary of team abbreviations to logo URLs"""
    # You can expand this with actual logo URLs
    return {
        # AFC East
        'BUF': 'https://example.com/logos/bills.png',
        'MIA': 'https://example.com/logos/dolphins.png',
        'NE': 'https://example.com/logos/patriots.png',
        'NYJ': 'https://example.com/logos/jets.png',
        # Add more teams as needed
    }

class NFLScheduleHelper:
    """Helper class for NFL schedule operations"""
    
    @staticmethod
    def get_primetime_games_for_week(week=None, year=None):
        """Get primetime games for a specific week"""
        from .models import Game
        
        if not year:
            year = timezone.now().year
        if not week:
            week = get_current_nfl_week()
        
        week_start, week_end = get_week_date_range(year, week)
        
        # Convert to datetime for filtering
        week_start_dt = timezone.datetime.combine(week_start, time.min)
        week_end_dt = timezone.datetime.combine(week_end, time.max)
        
        # Make timezone-aware
        eastern = pytz.timezone('US/Eastern')
        week_start_dt = eastern.localize(week_start_dt).astimezone(timezone.utc)
        week_end_dt = eastern.localize(week_end_dt).astimezone(timezone.utc)
        
        games = Game.objects.filter(
            start_time__gte=week_start_dt,
            start_time__lte=week_end_dt,
            sport='NFL'
        )
        
        return filter_primetime_games(games)
    
    @staticmethod
    def get_holiday_games():
        """Get all games scheduled on holidays"""
        from .models import Game
        
        now = timezone.now()
        holiday_dates = get_holiday_dates(now.year)
        
        return Game.objects.filter(
            start_time__date__in=holiday_dates.values(),
            sport='NFL'
        ).order_by('start_time')
    
    @staticmethod
    def get_games_needing_picks(user, league=None):
        """Get games that a user still needs to make picks for"""
        from .models import Game
        from apps.picks.models import Pick
        
        # Get games that can still have picks made
        pickable_games = Game.objects.pickable_games()
        
        # Filter to primetime games only
        primetime_games = filter_primetime_games(pickable_games)
        
        if not primetime_games:
            return []
        
        # Get games user has already picked
        existing_picks = Pick.objects.filter(
            user=user,
            league=league,
            game__in=primetime_games
        ).values_list('game_id', flat=True)
        
        # Return games without picks
        return [game for game in primetime_games if game.id not in existing_picks]