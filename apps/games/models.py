#apps/games/models.py
from django.db import models

class Game(models.Model):
    SPORT_CHOICES = [
        ('NFL', 'National Football League'),
        ('NBA', 'National Basketball Association'),
        # Future sports can be added here
    ]

    sport = models.CharField(max_length=10, choices=SPORT_CHOICES, default='NFL')
    home_team = models.CharField(max_length=100)
    away_team = models.CharField(max_length=100)
    start_time = models.DateTimeField()
    status = models.CharField(max_length=20, default='scheduled')  # scheduled, in_progress, final
    winner = models.CharField(max_length=100, blank=True, null=True)
    home_logo = models.URLField(blank=True, null=True)
    away_logo = models.URLField(blank=True, null=True)
    home_score = models.IntegerField(blank=True, null=True)
    away_score = models.IntegerField(blank=True, null=True)


    # Optional metadata
    game_week = models.IntegerField(blank=True, null=True)
    location = models.CharField(max_length=100, blank=True, null=True)
    external_id = models.CharField(max_length=100, blank=True, null=True)  # ID from external API (e.g. TheSportsDB)

    def __str__(self):
        return f"{self.get_sport_display()}: {self.away_team} at {self.home_team} ({self.start_time})"

    class Meta:
        ordering = ['start_time']
        verbose_name = "Game"
        verbose_name_plural = "Games"
