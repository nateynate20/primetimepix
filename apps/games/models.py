from django.db import models
from datetime import time
import pytz

class Game(models.Model):
    SPORT_CHOICES = [
        ('NFL', 'National Football League'),
        ('NBA', 'National Basketball Association'),
        # Add future sports here
    ]

    STATUS_CHOICES = [
        ('scheduled', 'Scheduled'),
        ('in_progress', 'In Progress'),
        ('final', 'Final'),
    ]

    sport = models.CharField(max_length=10, choices=SPORT_CHOICES, default='NFL')
    
    home_team = models.CharField(max_length=100)
    away_team = models.CharField(max_length=100)
    
    home_logo = models.URLField(blank=True, null=True)
    away_logo = models.URLField(blank=True, null=True)
    
    home_score = models.IntegerField(blank=True, null=True)
    away_score = models.IntegerField(blank=True, null=True)
    
    winner = models.CharField(max_length=100, blank=True, null=True)

    start_time = models.DateTimeField()
    location = models.CharField(max_length=100, blank=True, null=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')
    game_week = models.IntegerField(blank=True, null=True)
    
    # Make external_id unique to prevent duplicates
    external_id = models.CharField(max_length=100, unique=True, blank=True, null=True)
    
    # Optional: Add these fields for better NFL data management
    season = models.IntegerField(blank=True, null=True, help_text="NFL season year")
    game_type = models.CharField(max_length=10, blank=True, null=True, 
                                help_text="REG, WC, DIV, CON, SB")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def is_primetime(self):
        """Returns True if the game is considered a primetime game (8 PM ET or later)."""
        if not self.start_time:
            return False
            
        # Convert UTC time to Eastern Time for comparison
        eastern = pytz.timezone('US/Eastern')
        et_time = self.start_time.astimezone(eastern)
        return et_time.time() >= time(20, 0)  # 8:00 PM ET
    
    @property 
    def start_time_et(self):
        """Return the start time in Eastern Time"""
        if not self.start_time:
            return None
        eastern = pytz.timezone('US/Eastern')
        return self.start_time.astimezone(eastern)
    
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

    def __str__(self):
        primetime_indicator = " (PRIMETIME)" if self.is_primetime else ""
        return f"{self.get_sport_display()}: {self.away_team} at {self.home_team} ({self.start_time}){primetime_indicator}"

    class Meta:
        ordering = ['start_time']
        verbose_name = "Game"
        verbose_name_plural = "Games"
        # Add constraint to prevent duplicate external_ids
        constraints = [
            models.UniqueConstraint(
                fields=['external_id'], 
                name='unique_external_id_when_not_null',
                condition=models.Q(external_id__isnull=False)
            )
        ]