from django.db import models

class NFLGame(models.Model):
    event_id = models.CharField(max_length=50, unique=True)  # API unique event id
    week = models.CharField(max_length=10, null=True, blank=True)  # e.g., '1', '2', 'Wild Card'
    date = models.DateField()
    start_time = models.TimeField(null=True, blank=True)
    home_team = models.CharField(max_length=100)
    away_team = models.CharField(max_length=100)
    home_score = models.IntegerField(null=True, blank=True)
    away_score = models.IntegerField(null=True, blank=True)
    status = models.CharField(max_length=50, blank=True)  # "Scheduled", "Final", etc.
    home_logo = models.URLField(blank=True, null=True)
    away_logo = models.URLField(blank=True, null=True)

    def __str__(self):
        return f"{self.away_team} at {self.home_team} on {self.date}"
