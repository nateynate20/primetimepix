from django.db import models
from django.utils import timezone
import pytz
from datetime import time

class Game(models.Model):
    """Simplified Game model focused on NFL primetime pick'em flow.
    - Only 'NFL' is supported as sport.
    - Includes helper is_primetime() to determine primetime games.
    """

    SPORT_CHOICES = [
        ('NFL', 'National Football League'),
    ]

    STATUS_CHOICES = [
        ('scheduled', 'Scheduled'),
        ('in_progress', 'In Progress'),
        ('final', 'Final'),
        ('cancelled', 'Cancelled'),
    ]

    GAME_TYPE_CHOICES = [
        ('regular', 'Regular Season'),
        ('playoff', 'Playoff'),
        ('superbowl', 'Super Bowl'),
    ]

    game_id = models.CharField(max_length=100, unique=True, default="default_game_id")
    season = models.IntegerField()
    week = models.IntegerField()
    game_type = models.CharField(max_length=10)  # REG, POST, etc.
    start_time = models.DateTimeField(db_index=True)
    home_team = models.CharField(max_length=50)
    away_team = models.CharField(max_length=50)
    home_score = models.IntegerField(null=True, blank=True)
    away_score = models.IntegerField(null=True, blank=True)
    status = models.CharField(max_length=20, default='scheduled')

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['start_time']

    def __str__(self):
        return f"{self.away_team} @ {self.home_team} (Week {self.week})"

    @property
    def has_started(self):
        return timezone.now() >= self.start_time

    @property
    def is_finished(self):
        # normalize so final and finished are treated the same
        return self.status.lower() in ['final', 'finished']

    @property
    def is_primetime(self):
        """
        Return True if this game is considered 'primetime' (8:00 PM or later Eastern time).
        """
        if not self.start_time:
            return False
        try:
            eastern = pytz.timezone('US/Eastern')
            et_time = self.start_time.astimezone(eastern)
            return et_time.time() >= time(20, 0)  # 8:00 PM ET
        except Exception:
            return False

    def can_make_picks(self):
        """
        Return True if the game has not started yet, meaning the user can still make picks.
        """
        return not self.has_started
