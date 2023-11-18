#game_picks/models.py
from django.db import models
from django.contrib.auth.models import User

class GameSelection(models.Model):
    game = models.ForeignKey('nfl_schedule.NFLGame', on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    predicted_winner = models.CharField(max_length=50)

class UserRecord(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    correct_predictions = models.IntegerField()
    total_predictions = models.IntegerField()# Create your models here.
