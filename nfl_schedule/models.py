# nfl_schedule/models.py

from django.db import models
from django.utils import timezone

class NFLGame(models.Model):
    week = models.CharField(max_length=255, blank=True, null=True)
    date = models.DateField(default=timezone.now)
    home_team = models.CharField(max_length=255)
    away_team = models.CharField(max_length=255)
    start_time = models.CharField(max_length=255, blank=True, null=True)
    home_score = models.IntegerField(default=0)
    away_score = models.IntegerField(default=0)
    status = models.CharField(max_length=50, default="Scheduled")
    home_logo = models.URLField(blank=True, null=True)
    away_logo = models.URLField(blank=True, null=True)

    def __str__(self):
        return f"{self.home_team} vs {self.away_team} on {self.date} - {self.status}"
