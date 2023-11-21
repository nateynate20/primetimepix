#nfl_schedule/models.py
from django.db import models

class NFLGame(models.Model):
    week = models.CharField(max_length=255)
    date = models.DateField(default=1111-11-11)
    home_team = models.CharField(max_length=255)
    away_team = models.CharField(max_length=255)
    start_time = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.week}: {self.home_team} vs {self.away_team} ({self.start_time}) ({self.date})"
