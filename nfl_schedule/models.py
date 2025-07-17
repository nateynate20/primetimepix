#nfl_schedule/models.py
from django.db import models
from django.utils import timezone  # Django's timezone utility

class NFLGame(models.Model):
    week = models.CharField(max_length=255)
    date = models.DateField(default=timezone.now)  # <-- current date as default
    home_team = models.CharField(max_length=255)
    away_team = models.CharField(max_length=255)
    start_time = models.CharField(max_length=255)
    home_score = models.IntegerField(default=0)
    away_score = models.IntegerField(default=0)
    status = models.CharField(max_length=50, default="Scheduled")

    def __str__(self):
        return f"{self.week}: {self.home_team} vs {self.away_team} ({self.start_time}) ({self.date}) - {self.status}"
