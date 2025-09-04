# apps/games/utils.py

from datetime import datetime, time, timedelta
from django.utils import timezone
import pytz

# Define primetime start time (8:00 PM)
PRIMETIME_START = time(20, 0)


def filter_primetime_games(games_queryset):
    """
    Filter games queryset to only include primetime games (8 PM ET or later)
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


def get_current_nfl_week():
    """
    Calculate the current NFL week number.
    NFL season typically starts first week of September.
    This is a simplified version - you may want to make it more accurate.
    """
    try:
        now = timezone.now()
        current_date = now.date()
        
        # NFL season typically starts first Thursday after Labor Day
        # This is a simplified calculation
        year = current_date.year
        
        # Assume NFL season starts September 1st for simplicity
        season_start = datetime(year, 9, 1).date()
        
        if current_date < season_start:
            # Before season starts, return week 0 or previous year's week
            return 0
        
        # Calculate weeks since season start
        days_since_start = (current_date - season_start).days
        week_number = (days_since_start // 7) + 1
        
        # NFL regular season is typically 18 weeks, playoffs follow
        if week_number > 18:
            return 18  # Playoffs
        
        return max(1, week_number)
    
    except Exception:
        # Fallback to week 1 if calculation fails
        return 1


def get_current_week_dates():
    """Get the start and end dates for the current week (Monday to Sunday)"""
    today = timezone.now().date()
    days_since_monday = today.weekday()
    week_start = today - timedelta(days=days_since_monday)
    week_end = week_start + timedelta(days=6)
    return week_start, week_end


def is_primetime_game(game):
    """
    Check if a single game is a primetime game
    """
    try:
        # Check if game has is_primetime property first
        if hasattr(game, 'is_primetime'):
            return game.is_primetime
        
        # Fallback: check time manually
        eastern = pytz.timezone('US/Eastern')
        et_time = game.start_time.astimezone(eastern)
        return et_time.time() >= PRIMETIME_START
    
    except (AttributeError, TypeError):
        return False


def get_games_for_week(week_start_date, week_end_date):
    """
    Get games for a specific week date range
    """
    from .models import Game
    
    try:
        games = Game.objects.filter(
            start_time__date__gte=week_start_date,
            start_time__date__lte=week_end_date,
        ).order_by('start_time')
        
        return games
    except Exception:
        return Game.objects.none()


def get_completed_games():
    """
    Get all completed games (you may need to adjust status values)
    """
    from .models import Game
    
    try:
        # Adjust these status values based on what your Game model uses
        completed_statuses = ['FINAL', 'COMPLETED', 'F', 'final', 'completed']
        
        games = Game.objects.filter(
            status__in=completed_statuses
        ).order_by('-start_time')
        
        return games
    except Exception:
        return Game.objects.none()


def calculate_week_from_date(date_obj):
    """
    Calculate NFL week number from a given date
    """
    try:
        year = date_obj.year
        season_start = datetime(year, 9, 1).date()
        
        if date_obj < season_start:
            return 0
        
        days_since_start = (date_obj - season_start).days
        week_number = (days_since_start // 7) + 1
        
        return max(1, min(week_number, 18))
    
    except Exception:
        return 1