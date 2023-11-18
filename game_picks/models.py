#game_picks/models.py
from django.db import models
from django.contrib.auth.models import User

class GameSelection(models.Model):
    game = models.ForeignKey('nfl_schedule.NFLGame', on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    predicted_winner = models.CharField(max_length=50)
    is_correct = models.BooleanField(default=False)

class UserRecord(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    correct_predictions = models.IntegerField()
    total_predictions = models.IntegerField()# Create your models here.
    league = models.ForeignKey('League', on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.user.username}'s Record"

class League(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField()

    def __str__(self):
        return self.name