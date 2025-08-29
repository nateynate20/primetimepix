# apps/games/models.py
from django.db import models
from datetime import time
import pytz

class Game(models.Model):
    SPORT_CHOICES = [
        ('NFL', 'National Football League'),
        ('NBA', 'National Basketball Association'),
    ]

    STATUS_CHOICES = [
        ('scheduled', 'Scheduled'),
        ('in_progress', 'In Progress'),
        ('final', 'Final'),
        ('cancelled', 'Cancelled'),
        ('postponed', 'Postponed'),
    ]

    GAME_TYPE_CHOICES = [
        ('REG', 'Regular Season'),
        ('WC', 'Wild Card'),
        ('DIV', 'Divisional'),
        ('CON', 'Conference Championship'),
        ('SB', 'Super Bowl'),
    ]

    # Basic game info
    sport = models.CharField(max_length=10, choices=SPORT_CHOICES, default='NFL')
    external_id = models.CharField(max_length=100, unique=True, blank=True, null=True)
    
    # Teams
    home_team = models.CharField(max_length=100)
    away_team = models.CharField(max_length=100)
    home_logo = models.URLField(blank=True, null=True)
    away_logo = models.URLField(blank=True, null=True)
    
    # Scores
    home_score = models.IntegerField(blank=True, null=True)
    away_score = models.IntegerField(blank=True, null=True)
    winner = models.CharField(max_length=100, blank=True, null=True)

    # Game details
    start_time = models.DateTimeField()
    location = models.CharField(max_length=100, blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')
    
    # NFL specific
    game_week = models.IntegerField(blank=True, null=True)
    season = models.IntegerField(blank=True, null=True, help_text="NFL season year")
    game_type = models.CharField(max_length=10, choices=GAME_TYPE_CHOICES, 
                                blank=True, null=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['start_time']
        verbose_name = "Game"
        verbose_name_plural = "Games"
        constraints = [
            models.UniqueConstraint(
                fields=['external_id'], 
                name='unique_external_id_when_not_null',
                condition=models.Q(external_id__isnull=False)
            )
        ]

    @property
    def start_time_et(self):
        """Return the start time in Eastern Time"""
        if not self.start_time:
            return None
        eastern = pytz.timezone('US/Eastern')
        return self.start_time.astimezone(eastern)
    
    @property
    def is_primetime(self):
        """Returns True if the game is considered a primetime game (8 PM ET or later)."""
        if not self.start_time:
            return False
        et_time = self.start_time_et
        return et_time.time() >= time(20, 0)  # 8:00 PM ET
    
    @property
    def is_monday_night_football(self):
        """Returns True if this is a Monday Night Football game"""
        if not self.start_time or self.sport != 'NFL':
            return False
        et_time = self.start_time_et
        return et_time.weekday() == 0 and self.is_primetime  # Monday = 0
    
    @property
    def is_sunday_night_football(self):
        """Returns True if this is a Sunday Night Football game"""
        if not self.start_time or self.sport != 'NFL':
            return False
        et_time = self.start_time_et
        return et_time.weekday() == 6 and self.is_primetime  # Sunday = 6
    
    @property
    def is_thursday_night_football(self):
        """Returns True if this is a Thursday Night Football game"""
        if not self.start_time or self.sport != 'NFL':
            return False
        et_time = self.start_time_et
        return et_time.weekday() == 3 and self.is_primetime  # Thursday = 3

    @property
    def is_holiday_game(self):
        """Check if game is on a major holiday"""
        if not self.start_time:
            return False
        
        from .utils import get_holiday_dates
        holiday_dates = get_holiday_dates(self.start_time.year)
        return self.start_time.date() in holiday_dates.values()

    @property
    def game_status_display(self):
        """User-friendly status display"""
        status_map = {
            'scheduled': 'Upcoming',
            'in_progress': 'Live',
            'final': 'Final',
            'cancelled': 'Cancelled',
            'postponed': 'Postponed',
        }
        return status_map.get(self.status, self.status.title())

    @property
    def is_finished(self):
        """Check if game is completed"""
        return self.status in ['final']

    @property
    def is_live(self):
        """Check if game is currently in progress"""
        return self.status == 'in_progress'

    def can_make_picks(self):
        """Determine if picks can still be made for this game"""
        from django.utils import timezone
        return self.status == 'scheduled' and timezone.now() < self.start_time

    def get_winning_team(self):
        """Get the winning team name"""
        if not self.is_finished or self.home_score is None or self.away_score is None:
            return None
        
        if self.home_score > self.away_score:
            return self.home_team
        elif self.away_score > self.home_score:
            return self.away_team
        else:
            return 'TIE'  # Handle ties

    def __str__(self):
        primetime_indicator = " (PRIMETIME)" if self.is_primetime else ""
        date_str = self.start_time_et.strftime('%m/%d') if self.start_time_et else 'TBD'
        return f"{self.away_team} @ {self.home_team} - {date_str}{primetime_indicator}"


# New manager for common queries
class GameManager(models.Manager):
    def primetime_games(self):
        """Get all primetime games"""
        # This would need to be implemented with a custom SQL query
        # or filtered in Python due to timezone conversion complexity
        return self.get_queryset()
    
    def current_week_games(self):
        """Get games for the current NFL week"""
        from django.utils import timezone
        from datetime import timedelta
        
        now = timezone.now()
        week_start = now - timedelta(days=now.weekday())
        week_end = week_start + timedelta(days=7)
        
        return self.get_queryset().filter(
            start_time__gte=week_start,
            start_time__lt=week_end
        ).order_by('start_time')
    
    def pickable_games(self):
        """Get games that can still have picks made"""
        from django.utils import timezone
        
        return self.get_queryset().filter(
            status='scheduled',
            start_time__gt=timezone.now()
        ).order_by('start_time')

# Add the manager to the Game model
Game.add_to_class('objects', GameManager())